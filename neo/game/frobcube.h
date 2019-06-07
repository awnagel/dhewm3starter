// AN Frobcube, taken from Quadrilateral Cowboy source code.
#include "Entity.h"
#include "Misc.h"

class idFrobCube : public idStaticEntity
{
public:
	CLASS_PROTOTYPE( idFrobCube );

	void	Spawn( void );

	void	Save(idSaveGame *savefile) const;
	void	Restore(idRestoreGame *savefile);

	void	OnFrob( idEntity *activator);
private:
	idStr	functionName;
	idStr	masterName;
	bool	used;
	bool	useonce;
};
