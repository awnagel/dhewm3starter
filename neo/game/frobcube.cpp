// AN Frobcube, taken from Quadrilateral Cowboy source code.
#pragma hdrstop

#include "Game_local.h"
#include "frobcube.h"
#include "script\Script_Thread.h"
#include "Player.h"

CLASS_DECLARATION(idStaticEntity, idFrobCube )
END_CLASS

void idFrobCube::Save(idSaveGame *savefile) const
{
	savefile->WriteString(functionName);
	savefile->WriteString(masterName);
}

void idFrobCube::Restore(idRestoreGame *savefile)
{
	savefile->ReadString(functionName);
	savefile->ReadString(masterName);
}

void idFrobCube::Spawn(void)
{
	bool solid;
	solid = spawnArgs.GetBool("solid");
	if (solid)
	{
		this->GetPhysics()->SetContents(CONTENTS_SOLID);
	}

	useonce = spawnArgs.GetBool("useonce");
	used = false;

	functionName = NULL;
	functionName = spawnArgs.GetString("funcName");

	if (!functionName)
	{
		gameLocal.Warning("idFrobCube '%s' at (%s): cannot find funcName.", name.c_str(), GetPhysics()->GetOrigin().ToString(0));
	}

	masterName = NULL;
	masterName = spawnArgs.GetString("owner");

	if (!masterName)
	{
		gameLocal.Warning("idFrobCube '%s' at (%s): cannot find owner.", name.c_str(), GetPhysics()->GetOrigin().ToString(0));
	}
}

void idFrobCube::OnFrob(idEntity *activator)
{
	idStr hideName = spawnArgs.GetString("hidename");
	if (hideName)
	{
		idEntity *hideEnt = gameLocal.FindEntity(hideName);

		if (hideEnt)
		{
			hideEnt->Hide();
		}
	}

	// call script
	idStr scriptName = spawnArgs.GetString("call");
	const function_t *scriptFunction;
	scriptFunction = gameLocal.program.FindFunction(scriptName);
	if (scriptFunction && !used)
	{
		if (useonce)
		{
			used = true;
			common->Printf(va("%d", used));
		}

		idThread *thread;
		thread = new idThread( scriptFunction );
		thread->DelayedStart(0);
	}

	if (spawnArgs.GetBool("gettable"))
	{
		// Get code here
		return;
	}

	idEntity *ownerEnt = gameLocal.FindEntity(masterName);

	if (!ownerEnt)
	{
		//gameLocal.Warning( "idFrobCube '%s' at (%s): owner '%s' doesn't exist.", name.c_str(), GetPhysics()->GetOrigin().ToString(0), masterName );
		return;
	}

	gameLocal.GetLocalPlayer()->UseFrob(ownerEnt, functionName);
}