#ifndef INC_POUS_PATCH_H_
#define INC_POUS_PATCH_H_

void set_callback(void *addr);


#undef __SET_LOCATED
#define __SET_LOCATED(prefix, name, suffix, new_value)\
if (!(prefix name.flags & __IEC_FORCE_FLAG)) *(prefix name.value) suffix = new_value;\
	set_callback(&(prefix name))
#undef __SET_VAR
#define __SET_VAR(prefix, name, suffix, new_value)\
if (!(prefix name.flags & __IEC_FORCE_FLAG)) prefix name.value suffix = new_value;\
	set_callback(&(prefix name))

#endif /* INC_POUS_PATCH_H_ */
