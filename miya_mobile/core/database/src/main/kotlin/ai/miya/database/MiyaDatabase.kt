package ai.miya.database

import android.content.Context
import androidx.room.Room
import androidx.room.RoomDatabase

abstract class MiyaDatabase : RoomDatabase() {

    companion object {
        @Volatile
        private var instance: MiyaDatabase? = null

        fun getInstance(context: Context): MiyaDatabase {
            return instance ?: synchronized(this) {
                instance ?: Room.databaseBuilder(
                    context.applicationContext,
                    MiyaDatabase::class.java,
                    "miya_cache.db"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                    .also { instance = it }
            }
        }
    }
}
