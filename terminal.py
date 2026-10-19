import random as rd

you = 'gay'
want_to_run_file = True
error_raised = rd.randint(0,1)

if you == want_to_run_file:
    type('python main.py')
elif error_raised:
    type('fuser -k 8000/tcp')
else:
    print('FU')