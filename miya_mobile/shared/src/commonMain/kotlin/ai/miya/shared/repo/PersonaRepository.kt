package ai.miya.shared.repo

import ai.miya.shared.api.MiyaApiClient
import ai.miya.shared.model.*

class PersonaRepository(
    private val api: MiyaApiClient,
) {
    suspend fun getList(): List<Persona> = api.getPersonaList()

    suspend fun getCurrent(): PersonaCurrentResponse = api.getCurrentPersona()

    suspend fun switch(personalityId: String): SwitchPersonaResponse {
        return api.switchPersona(personalityId)
    }
}
