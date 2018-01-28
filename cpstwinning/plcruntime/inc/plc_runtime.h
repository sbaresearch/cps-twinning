#ifndef INC_PLC_RUNTIME_H_
#define INC_PLC_RUNTIME_H_

#define __LOCATED_VAR(type, name, ...) type __##name;
#include <LOCATED_VARIABLES.h>
#undef __LOCATED_VAR
#define __LOCATED_VAR(type, name, ...) type* name = &__##name;
#include <LOCATED_VARIABLES.h>
#undef __LOCATED_VAR

#endif /* INC_PLC_RUNTIME_H_ */
