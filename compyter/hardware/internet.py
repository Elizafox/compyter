from . import intc
from ..util import in_range, set_word_byte, get_word_byte
import threading
import ipaddress
import socket
import selectors
import errno


class Internet(intc.InterruptHardware):
    INT_NUM = 192

    ADDR_BEGIN = 0xffffe94f
    ADDR_END =   0xffffedaf

    MAXBUFSIZE = 0x400

    # Command registers
    REG_ADDR = 0x0              # 0xffffe94f
    REG_IP_VER = 0x10           # 0xffffe95f
    REG_IP_PROTO = 0x14         # 0xffffe963
    REG_HANDLE = 0x18           # 0xffffe967
    REG_COMMAND = 0x1c          # 0xffffe96b
    REG_PARAMS = 0x20           # 0xffffe96f
    REG_STATUS = 0x24           # 0xffffe973

    # Asynchronous operation registers
    REG_ASYNC_OP = 0x28         # 0xffffe977
    REG_ASYNC_HANDLE = 0x2c     # 0xffffe97b

    # Buffer
    REG_BUFSIZE = 0x5c          # 0xffffe9ab
    REG_BUFFER = 0x60           # 0xffffe9af

    # Command types
    CMD_NOP = 0x00
    CMD_SOCKET = 0x01
    CMD_BIND = 0x02
    CMD_CONNECT = 0x03
    CMD_LISTEN = 0x04
    CMD_ACCEPT = 0x05
    CMD_CLOSE = 0x06
    CMD_SETSOCKOPT = 0x07
    CMD_GETSOCKOPT = 0x08
    CMD_RECV = 0x09
    CMD_SEND = 0x0a
    CMD_RECVFROM = 0x0b
    CMD_SENDTO = 0x0c
    CMD_GETADDRINFO = 0x0d
    CMD_GETNAMEINFO = 0x0e
    CMD_ASYNC_START = 0x0f
    CMD_ASYNC_STOP = 0x10
    CMD_ASYNC_DONE = 0x11

    # Async operation event masks
    ASYNC_READ = 0x1
    ASYNC_WRITE = 0x2

    VER_IPV4 = 0x1
    VER_IPV6 = 0x2

    PROTO_TCP = 0x1
    PROTO_UDP = 0x2
    
    def __init__(self, cpu, memory, intc):
        super().__init__(cpu, memory, intc)

        self.addr = 0
        self.ip_ver = 0
        self.proto = 0
        self.command = 0
        self.result = 0
        self.current_handle = -1
        self.params = 0
        self.status = 0
        self.bufsize = self.MAXBUFSIZE
        self.buffer = bytearray(self.bufsize)

        self.async_op = 0
        self.async_handle = 0
        self.async_done = threading.Event()

        self.sockets = {}

        self.selector = selectors.DefaultSelector()

        self.async_thread = threading.Thread(target=self.process_async, daemon=True)
        self.async_thread.start()
        self.cpu.register_thread(self.async_thread)

    def process_async(self):
        while not self.cpu.exit_event.is_set():
            events = self.selector.select(10)
            for key, mask in events:
                self.async_op = 0
                self.async_done.clear()

                if mask & selectors.EVENT_READ:
                    self.async_op |= self.ASYNC_READ

                if mask & selectors.EVENT_WRITE:
                    self.async_op |= self.ASYNC_WRITE

                self.async_handle = key.fd
                self.interrupt()

                # Wait for the operation to finish before firing another interrupt
                self.async_done.wait()

    @staticmethod
    def _set_quad_byte(num, byte, val):
        mask_table = [
            0xffffffffffffffffffffffffffffff00,
            0xffffffffffffffffffffffffffff00ff,
            0xffffffffffffffffffffffffff00ffff,
			0xffffffffffffffffffffffff00ffffff,
			0xffffffffffffffffffffff00ffffffff,
			0xffffffffffffffffffff00ffffffffff,
			0xffffffffffffffffff00ffffffffffff,
			0xffffffffffffffff00ffffffffffffff,
			0xffffffffffffff00ffffffffffffffff,
			0xffffffffffff00ffffffffffffffffff,
			0xffffffffff00ffffffffffffffffffff,
			0xffffffff00ffffffffffffffffffffff,
			0xffffff00ffffffffffffffffffffffff,
			0xffff00ffffffffffffffffffffffffff,
			0xff00ffffffffffffffffffffffffffff,
			0x00ffffffffffffffffffffffffffffff,
        ]

        val &= 0xff
        byte = 15 - byte
        return (mask_table[byte] & num) | (val << (byte * 8))

    @staticmethod
    def _get_quad_byte(num, byte):
        return (num >> ((15 - byte) * 8)) & 0xff
    
    def _set_error(self, err, strerror=None):
        if strerror is None:
            if err > 0:
                strerror = os.strerror(errno)
            elif err == 0:
                strerror = ""
            else:
                strerror = os.strerror(-err)

        if strerror:
            strerror = strerror.encode() + b"\x00"
            strerror_len = len(strerror)
            self.buflen = strerror_len
            self.buffer[0:strerror_len] = strerror

        self.status = (-err if err > 0 else err)

    def _sock_ip_ver(self, sock):
        if sock.family == socket.AF_INET:
            return self.VER_IPV4
        elif sock.family == socket.AF_INET6:
            return self.VER_IPV6
        else:
            raise NotImplementedError("Invalid protocol")

    def _int_to_addr(self, ip_ver, addr):
        if ip_ver == self.VER_IPV4:
            addr = ipaddress.IPv4Address(addr)
        elif ip_ver == self.VER_IPV6:
            addr = ipaddress.IPv6Address(addr)
        else:
            raise NotImplementedError("Invalid protocol")

        return addr

    def _cmd_nop(self):
        return

    def _cmd_socket(self):
        ip_ver = 0
        if self.ip_ver == self.VER_IPV4:
            ip_ver = socket.AF_INET
        elif self.ip_ver == self.VER_IPV6:
            ip_ver = socket.AF_INET6

        proto = 0
        if self.proto == self.PROTO_TCP:
            proto = socket.SOCK_STREAM
        elif self.proto == self.PROTO_UDP:
            proto = socket.SOCK_DGRAM

        try:
            sock = socket.socket(ip_ver, proto)
        except OSError as e:
            self.current_handle = 0
            self._set_error(e.errno, e.strerror)
            return

        self._set_error(0)
        self.current_handle = sock.fileno()
        self.sockets[sock.fileno()] = [sock]

    def _cmd_bind(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]
        try:
            addr = self._int_to_addr(self._sock_ip_ver(sock), self.addr)
        except Exception as e:
            self._set_error(errno.EINVAL, str(e))
            return

        try:
            sock.bind((str(addr), self.params & 0xffff))
        except OSError as e:
            self._set_error(e.errno, e.strerror)
            return

        self._set_error(0)

    def _cmd_connect(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]
        try:
            addr = self._int_to_addr(self._sock_ip_ver(sock), self.addr)
        except Exception as e:
            self._set_error(errno.EINVAL, str(e))
            return

        try:
            sock.connect((str(addr), self.params & 0xffff))
        except OSError as e:
            self._set_error(e.errno, e.strerror)
            return

        self._set_error(0)

    def _cmd_listen(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]
        try:
            sock.listen(self.params)
        except OSError as e:
            self._set_error(e.errno, e.strerror)
            return

        self._set_error(0)

    def _cmd_accept(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]
        try:
            conn, addr = sock.accept()
        except OSError as e:
            self._set_error(e.errno, e.strerror)
            return

        self.addr = int(ipaddress.ip_address(addr[0]))
        self.params = addr[1]
        self.sockets[conn.fileno()] = [conn]
        self.current_handle = conn.fileno()

        self._set_error(0)

    def _cmd_close(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]
        try:
            sock.close()
        except OSError as e:
            # There's not much we can do about this
            pass

        del self.sockets[self.current_handle]
        self._set_error(0)

    def _cmd_setsockopt(self):
        # TODO
        self._set_error(errno.ENOSYS)

    def _cmd_getsockopt(self):
        # TODO
        self._set_error(errno.ENOSYS)

    def _cmd_recv(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]
        flags = 0
        if self.params:
            flags |= socket.MSG_OOB

        try:
            data = sock.recv(self.MAXBUFSIZE, flags)
        except OSError as e:
            self._set_error(e.errno, e.strerror)
            return

        datalen = len(data)
        self.bufsize = datalen
        self.buffer[0:datalen] = data

        self._set_error(0)

    def _cmd_send(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]
        flags = 0
        if self.params:
            flags |= socket.MSG_OOB

        try:
            datalen = sock.send(self.buffer[0:self.bufsize], flags)
        except OSError as e:
            self._set_error(e.errno, e.strerror)
            return

        self.params = datalen

        self._set_error(0)

    def _cmd_recvfrom(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]
        flags = 0
        if self.params:
            flags |= socket.MSG_OOB

        try:
            data, addr = sock.recvfrom(self.MAXBUFSIZE, flags)
        except OSError as e:
            self._set_error(e.errno, e.strerror)
            return

        self.addr = int(ipaddress.ip_address(addr))
        datalen = len(data)
        self.bufsize = datalen
        self.buffer[0:datalen] = data

        self._set_error(0)

    def _cmd_sendto(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]
        flags = 0
        if self.status:
            flags |= socket.MSG_OOB

        try:
            addr = str(ipaddress.ip_address(self.addr))
        except Exception as e:
            self._set_error(errno.EINVAL, str(e))
            return

        try:
            datalen = sock.sendto(self.buffer[0:self.bufsize], flags,
                                  (addr, self.params & 0xffff))
        except OSError as e:
            self._set_error(e.errno, e.strerror)
            return

        self.params = datalen

        self._set_error(0)

    def _cmd_getaddrinfo(self):
        addr = self.buffer[0:self.buflen].decode("ascii")

        try:
            ai = getaddrinfo(addr, self.params & 0xffff)
        except socket.gaierror as e:
            self._set_error(e.errno, e.strerror)
            return

        bufpos = 0
        for info in ai:
            if info[0] == socket.AF_INET:
                ip_ver = self.VER_IPV4
            elif info[0] == socket.AF_INET6:
                ip_ver = self.VER_IPV6

            addr = ipaddress.ip_address(info[4][0])

            self.buffer[bufpos:bufpos+4] = ip_ver.to_bytes(4, "big")
            self.buffer[bufpos+4:bufpos+20] = int(addr).to_bytes(16, "big")

            if bufpos + 20 >= self.MAXBUFSIZE:
                break
            
            bufpos += 20

        self.bufsize = bufpos

        self._set_error(0)

    def _cmd_getnameinfo(self):
        try:
            addr = str(self._int_to_addr(self.ip_ver, self.addr))
        except Exception as e:
            self._set_error(errno.EINVAL, str(e))
            return

        try:
            host = self.buffer[0:self.buflen].decode("ascii")
        except Exception as e:
            self._set_error(errno.EINVAL, str(e))
            return

        host, _ = socket.getnameinfo((host, 0), socket.NI_NUMERICSERV|socket.NI_NOFQDN)

        host = host[0:self.MAXBUFSIZE].encode("idna")  # Truncate, just in case
        self.bufsize = len(host)
        self.buffer[0:self.bufsize] = host

        self._set_error(0)

    def _cmd_async_start(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]

        mask = 0
        if self.params & self.ASYNC_READ:
            mask |= selectors.EVENT_READ

        if self.params & self.ASYNC_WRITE:
            mask |= selectors.EVENT_WRITE

        sock.setblocking(False)
        self.selector.register(sock, mask, None)

        self._set_error(0)

    def _cmd_async_stop(self):
        if self.current_handle not in self.sockets:
            return

        sock = self.sockets[self.current_handle][0]
        self.selector.unregister(sock)
        self._set_error(0)

    def _cmd_async_done(self):
        self.async_done.set()
        self._set_error(0)

    CMD_TABLE = {
        CMD_NOP : _cmd_nop,
        CMD_SOCKET : _cmd_socket,
        CMD_BIND : _cmd_bind,
        CMD_CONNECT : _cmd_connect,
        CMD_LISTEN : _cmd_listen,
        CMD_ACCEPT : _cmd_accept,
        CMD_CLOSE : _cmd_close,
        CMD_SETSOCKOPT : _cmd_setsockopt,
        CMD_GETSOCKOPT : _cmd_getsockopt,
        CMD_RECV : _cmd_recv,
        CMD_SEND : _cmd_send,
        CMD_RECVFROM : _cmd_recvfrom,
        CMD_SENDTO : _cmd_sendto,
        CMD_GETADDRINFO : _cmd_getaddrinfo,
        CMD_GETNAMEINFO : _cmd_getnameinfo,
        CMD_ASYNC_START : _cmd_async_start,
        CMD_ASYNC_STOP : _cmd_async_stop,
        CMD_ASYNC_DONE: _cmd_async_done,
    }

    def __getitem__(self, item):
        if in_range(item, self.REG_ADDR, self.REG_ADDR + 15):
            return self._get_quad_byte(self.addr, item)
        elif in_range(item, self.REG_IP_VER, self.REG_IP_VER + 3):
            return get_word_byte(self.ip_ver, item - self.REG_IP_VER)
        elif in_range(item, self.REG_IP_PROTO, self.REG_IP_PROTO + 3):
            return get_word_byte(self.proto, item - self.REG_IP_PROTO)
        elif in_range(item, self.REG_HANDLE, self.REG_HANDLE + 3):
            return get_word_byte(self.current_handle, item - self.REG_HANDLE)
        elif in_range(item, self.REG_COMMAND, self.REG_COMMAND + 3):
            return get_word_byte(self.command, item - self.REG_COMMAND)
        elif in_range(item, self.REG_PARAMS, self.REG_PARAMS + 3):
            return get_word_byte(self.params, item - self.REG_PARAMS)
        elif in_range(item, self.REG_STATUS, self.REG_STATUS + 3):
            return get_word_byte(self.status, item - self.REG_STATUS)
        elif in_range(item, self.REG_ASYNC_OP, self.REG_ASYNC_OP + 3):
            return get_word_byte(self.async_op, item - self.REG_ASYNC_OP)
        elif in_range(item, self.REG_ASYNC_HANDLE, self.REG_ASYNC_HANDLE + 3):
            return get_word_byte(self.async_handle, item - self.REG_ASYNC_HANDLE)
        elif in_range(item, self.REG_BUFSIZE, self.REG_BUFSIZE + 3):
            return get_word_byte(self.bufsize, item - self.REG_BUFSIZE)
        elif in_range(item, self.REG_BUFFER, self.REG_BUFFER + (self.MAXBUFSIZE - 1)):
            return self.buffer[item - self.REG_BUFSIZE]
        else:
            return 0
    
    def __setitem__(self, item, val):
        if in_range(item, self.REG_ADDR, self.REG_ADDR + 15):
            self.addr = self._set_quad_byte(self.addr, item, val)
        elif in_range(item, self.REG_IP_VER, self.REG_IP_VER + 3):
            self.ip_ver = set_word_byte(self.ip_ver, item - self.REG_IP_VER, val)
        elif in_range(item, self.REG_IP_PROTO, self.REG_IP_PROTO + 3):
            self.proto = set_word_byte(self.proto, item - self.REG_IP_PROTO, val)
        elif in_range(item, self.REG_HANDLE, self.REG_HANDLE + 3):
            self.current_handle = set_word_byte(self.current_handle, item - self.REG_HANDLE, val)
        elif in_range(item, self.REG_COMMAND, self.REG_COMMAND + 3):
            self.command = set_word_byte(self.command, item - self.REG_COMMAND, val)
            if item != self.REG_COMMAND + 3:
                # Only act when the last byte is written
                return

            if self.command not in self.CMD_TABLE:
                return

            self.CMD_TABLE[self.command](self)
        elif in_range(item, self.REG_PARAMS, self.REG_PARAMS + 3):
            self.params = set_word_byte(self.params, item - self.REG_PARAMS, val)
        elif in_range(item, self.REG_STATUS, self.REG_STATUS + 3):
            self.status = set_word_byte(self.status, item - self.REG_PARAMS, val)
        elif in_range(item, self.REG_ASYNC_OP, self.REG_ASYNC_OP + 3):
            self.async_op = set_word_byte(self.async_op, item - self.REG_ASYNC_OP, val)
        elif in_range(item, self.REG_ASYNC_HANDLE, self.REG_ASYNC_HANDLE + 3):
            self.async_handle = set_word_byte(self.async_handle, item - self.REG_ASYNC_HANDLE, val)
        elif in_range(item, self.REG_BUFSIZE, self.REG_BUFSIZE + 3):
            self.bufsize = set_word_byte(self.bufsize, item - self.REG_BUFSIZE, val)
            if self.bufsize > self.MAXBUFSIZE:
                self.bufsize %= self.MAXBUFSIZE
        elif in_range(item, self.REG_BUFFER, self.REG_BUFFER + (self.MAXBUFSIZE - 1)):
            self.buffer[item - self.REG_BUFFER] = val
