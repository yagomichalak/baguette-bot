from typing import List

def get_mute_time(time: List[str]) -> int:
	""" Gets the mute time in seconds.
	:param ctx: The context.
	:param time: The given time. """
	
	keys = ['d', 'h', 'm', 's']
	for k in keys:
		if k in time:
			break
	else:
		print("Inform a valid time")
		return

	the_time_dict = {
		'days': 0,
		'hours': 0,
		'minutes': 0,
		'seconds': 0,
	}


	for t in time.split():

		if 'd' in t and t[:-1].isdigit():
			the_time_dict['days'] = int(t[:-1])
		if 'h' in t and t[:-1].isdigit():
			the_time_dict['hours'] = int(t[:-1])
		if 'm' in t and t[:-1].isdigit():
			the_time_dict['minutes'] = int(t[:-1])
		if 's' in t and t[:-1].isdigit():
			the_time_dict['seconds'] = int(t[:-1])

	if sum(the_time_dict.values()) <= 0:
		print("Something is wrong with it")
		return False
		
	return the_time_dict


text = ''
text = '1d1 s2s'

seconds = get_mute_time(text)

print(seconds)
# print(algo[:-1].isdigit())
# print('1d 2h'.split('h'))