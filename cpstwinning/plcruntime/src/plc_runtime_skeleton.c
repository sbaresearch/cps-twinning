#include <stdio.h>
#include <string.h>
#include <time.h>
#include <signal.h>
#include <unistd.h>
#include <pthread.h>
#include <semaphore.h>

#include "iec_types.h"
#include "iec_std_lib.h"

#include <POUS.h>
#include <plc_runtime.h>

void config_run__(int tick);
void config_init__(void);

void plc_thread_routine_c(void *arg);
void init_plc(void *arg);
int start_plc(void);
int stop_plc(void);
void run(long int tv_sec, long int tv_nsec);
void init_timer(struct itimerspec *timer_values, sigevent_t *sigev);
int get_ref_by_idx(int idx, void ***ptr);
int get_len_of_vars_arr(void);
int set_int_val_by_idx(int idx, void *ptr);
int do_notify(int idx);
void register_var_change_callback(void (*clbk)(int));
void set_callback(void *addr);

TIME __CURRENT_TIME;
uint8_t __DEBUG = 0;

static int tick = 0;

extern int common_ticktime__;

int is_plc_running = 0;
pthread_t plc_thread;
sem_t sem_plc_timer;
sem_t sem_plc_vars;
timer_t timer;

// PROGRAM

static void *vars[] =
{
// PLC_VARS
		};

static int vars_len = sizeof(vars) / sizeof(vars[0]);

void (*notify_var_change_callback)(int) = NULL;

void set_callback(void *addr)
{

	int i = 0;
	for (i; i < vars_len; i++)
	{
		if (addr == vars[i])
		{
			// Notify var change via Python ctypes callback function
			int err = do_notify(i);
			if (err)
				printf(
						"Error: Could not notify change of variable: %d (idx).\n",
						i);
		}
	}
}

void register_var_change_callback(void (*clbk)(int))
{
	notify_var_change_callback = clbk;
#ifdef DEBUG
	printf("Callback set!\n");
#endif
}

int do_notify(int idx)
{
	if (notify_var_change_callback)
	{
#ifdef DEBUG
		printf("Notify now!\n");
#endif
		notify_var_change_callback(idx);
		return 0;
	}
	return -1;
}

int get_len_of_vars_arr(void)
{
	int len = (int) (sizeof(vars) / sizeof(vars[0]));
#ifdef DEBUG
	printf("Length of array: %d.\n", len);
#endif
	return len;
}

int set_int_val_by_idx_p(int idx, void *ptr)
{
	if (get_len_of_vars_arr() < idx)
		return -1;
	void **var_ptr = vars[idx];
	int **var = ((int **) var_ptr);
#ifdef DEBUG
	printf("Value of idx: %d before change is: %d.\n", idx, **var);
#endif
	sem_wait(&sem_plc_vars);
	**var = *((int *) ptr);
#ifdef DEBUG
	printf("Value of idx: %d after change is: %d.\n", idx, **var);
#endif
	return 0;
}

int set_int_val_by_idx_t(int idx, void *ptr)
{
	if (get_len_of_vars_arr() < idx)
		return -1;
	void *var_ptr = vars[idx];
	int *var = ((int *) var_ptr);
#ifdef DEBUG
	printf("Value of idx: %d before change is: %d.\n", idx, *var);
#endif
	sem_wait(&sem_plc_vars);
	*var = *((int *) ptr);
#ifdef DEBUG
	printf("Value of idx: %d after change is: %d.\n", idx, *var);
#endif
	return 0;
}

int get_ref_by_idx_t(int idx, void **ptr)
{
	if (get_len_of_vars_arr() < idx)
		return -1;
	*ptr = vars[idx];
	return 0;
}

int get_ref_by_idx_p(int idx, void ***ptr)
{
	if (get_len_of_vars_arr() < idx)
		return -1;
	*ptr = vars[idx];
	return 0;
}

void run(long int tv_sec, long int tv_nsec)
{

#ifdef DEBUG
	printf("Tick %d\n", tick);
#endif
	config_run__(tick++);

}

void get_time(IEC_TIME *CURRENT_TIME)
{
    struct timespec tmp_time;
    clock_gettime(CLOCK_REALTIME, &tmp_time);
    CURRENT_TIME->tv_sec = tmp_time.tv_sec;
    CURRENT_TIME->tv_nsec = tmp_time.tv_nsec;
}

void timer_notify(sigval_t val)
{
	get_time(&__CURRENT_TIME);
	sem_post(&sem_plc_timer);
}

void catch_signal(int sig)
{
#ifdef DEBUG
	printf("Got signal %d.\n", sig);
#endif
	if (is_plc_running)
		stop_plc();
}

void init_timer(struct itimerspec *timer_values, sigevent_t *sigev)
{
	long tv_nsec = common_ticktime__ % 1000000000;
	time_t tv_sec = common_ticktime__ / 1000000000;

	memset(sigev, 0, sizeof(struct sigevent));
	memset(timer_values, 0, sizeof(struct itimerspec));
	sigev->sigev_value.sival_int = 0;
	sigev->sigev_notify = SIGEV_THREAD;
	sigev->sigev_notify_attributes = NULL;
	sigev->sigev_notify_function = timer_notify;
	timer_values->it_value.tv_sec = tv_sec;
	timer_values->it_value.tv_nsec = tv_nsec;
	timer_values->it_interval.tv_sec = tv_sec;
	timer_values->it_interval.tv_nsec = tv_nsec;
}

void plc_thread_routine_c(void *arg)
{

	while (is_plc_running)
	{
		sem_post(&sem_plc_vars);
		sem_wait(&sem_plc_timer);
		run(__CURRENT_TIME.tv_sec, __CURRENT_TIME.tv_nsec);
	}
#ifdef DEBUG
	printf("Exit PLC thread.\n");
#endif
	pthread_exit(0);

}

// Can be called before starting the PLC to set initial values.
void init_plc(void *arg)
{
	if (!is_plc_running)
		return;

// TODO

}

int start_plc(void)
{

	int err = 0;
	is_plc_running = 1;

	err = sem_init(&sem_plc_timer, 0, 0);
	if (err < 0)
	{
		printf("Failed to initialize semaphore for timer.\n");
		return err;
	}

	err = sem_init(&sem_plc_vars, 0, 0);
	if (err < 0)
	{
		printf("Failed to initialize semaphore for PLC vars.\n");
		return err;
	}

	err = pthread_create(&plc_thread, NULL, (void*) &plc_thread_routine_c,
			NULL);
	if (err)
	{
		printf("Failed to create thread.\n");
		return err;
	}

	sigevent_t sigev;
	struct itimerspec timer_values;

	init_timer(&timer_values, &sigev);

#ifdef DEBUG
	printf("Tick-time is: %d ns.\nTimer values: sec = %ld, nsec = %ld.\n", common_ticktime__, timer_values.it_interval.tv_sec, timer_values.it_interval.tv_nsec);
#endif

	config_init__();

	err = timer_create(CLOCK_REALTIME, &sigev, &timer);
	if (err < 0)
	{
		printf("Failed to create timer\n.");
		return err;
	}

	err = timer_settime(timer, 0, &timer_values, NULL);
	if (err < 0)
	{
		printf("Failed to arm or disarm the timer.\n");
		return err;
	}
	/* Install signal handler for manual break. */
	signal(SIGTERM, catch_signal);
	signal(SIGINT, catch_signal);

	return 0;
}

int stop_plc(void)
{
	if (!is_plc_running)
		return 0;

	int err = 0;
	is_plc_running = 0;
	err = pthread_join(plc_thread, NULL);
	if (err)
	{
		printf("Failed to wait for thread.\n");
		return err;
	}
#ifdef DEBUG
	else
	printf("Joined PLC thread.\n");
#endif
	err = sem_destroy(&sem_plc_timer);
	if (err < 0)
	{
		printf("Failed to destroy semaphore for timer.\n");
		return err;
	}
	err = sem_destroy(&sem_plc_vars);
	if (err < 0)
	{
		printf("Failed to destroy semaphore for PLC vars.\n");
		return err;
	}
	err = timer_delete(timer);
	if (err < 0)
	{
		printf("Failed to delete timer.\n");
		return err;
	}
	return 0;
}
