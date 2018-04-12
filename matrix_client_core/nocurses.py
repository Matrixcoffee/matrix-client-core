# Because friends don't let friends use (n)curses

colors = dict((y, x) for x, y in enumerate("black red green yellow blue magenta cyan grey".split()))

def _parse_color(color):
	# return a value between 0 and 7 inclusive, representing a base ansi color value
	if isinstance(color, str):
		if color.lower() in colors: color = colors[color]
		else: raise ValueError("%s is not a known color" % repr(color))
	elif not isinstance(color, int): raise TypeError("Argument type must be either 'int' or 'str'")
	if color < 0 or color > 7: raise ValueError("Color value '%i' does not lie between 0 and 7, inclusive")
	return color

_real_print = print

def print(*args, **kwargs):
	# Just like builtin print(), but you can add fg= and bg= color keywords

	# Intentionally simple. The whole output will be in the specified color.
	colors = []
	if 'fg' in kwargs:
		fg = _parse_color(kwargs['fg']) + 30
		colors.append(str(fg))
		del kwargs['fg']
	if 'bg' in kwargs:
		bg = _parse_color(kwargs['bg']) + 40
		colors.append(str(bg))
		del kwargs['bg']

	if len(args) > 0 and len(colors) > 0:
		ansiseq = "\x1b[" + ";".join(colors) + "m"
		args = (ansiseq + args[0],) + args[1:] + ("\x1b[0m",)

	_real_print(*args, **kwargs)

if __name__ == '__main__':
	print("Hello world!", fg='red')
