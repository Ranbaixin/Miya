package ai.miya.android.ui.chat

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import ai.miya.android.ui.theme.*
import java.io.File

@Composable
fun rememberImagePicker(): ImagePickerState {
    val context = LocalContext.current

    var selectedImageUri by remember { mutableStateOf<Uri?>(null) }
    var cameraFileUri by remember { mutableStateOf<Uri?>(null) }

    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success ->
        if (success && cameraFileUri != null) {
            selectedImageUri = cameraFileUri
        }
    }

    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) {
            selectedImageUri = uri
        }
    }

    fun launchCamera() {
        val file = File(context.cacheDir, "miya_photo_${System.currentTimeMillis()}.jpg")
        cameraFileUri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file
        )
        cameraFileUri?.let { cameraLauncher.launch(it) }
    }

    fun launchGallery() {
        galleryLauncher.launch("image/*")
    }

    return ImagePickerState(
        selectedImageUri = selectedImageUri,
        onLaunchCamera = { launchCamera() },
        onLaunchGallery = { launchGallery() },
        onClearSelected = { selectedImageUri = null },
        onImageResult = { uri -> selectedImageUri = uri },
    )
}

data class ImagePickerState(
    val selectedImageUri: Uri?,
    val onLaunchCamera: () -> Unit,
    val onLaunchGallery: () -> Unit,
    val onClearSelected: () -> Unit,
    val onImageResult: (Uri) -> Unit,
)

@Composable
fun ImageSourceSheet(
    onDismiss: () -> Unit,
    onCamera: () -> Unit,
    onGallery: () -> Unit,
) {
    Surface(
        color = MiyaSurfaceDeep.copy(alpha = 0.95f),
        shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp),
        tonalElevation = 8.dp,
    ) {
        Column(modifier = Modifier.padding(vertical = 16.dp)) {
            Text(
                text = "发送图片",
                color = MiyaTextPrimary,
                fontSize = 16.sp,
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 8.dp),
            )

            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.SpaceEvenly,
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(12.dp),
                ) {
                    Surface(
                        onClick = onCamera,
                        shape = RoundedCornerShape(16.dp),
                        color = MiyaSurface,
                        modifier = Modifier.size(64.dp),
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(
                                Icons.Filled.CameraAlt, "拍照",
                                tint = MiyaAccent, modifier = Modifier.size(28.dp),
                            )
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    Text("拍照", color = MiyaTextSecondary, fontSize = 12.sp)
                }

                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(12.dp),
                ) {
                    Surface(
                        onClick = onGallery,
                        shape = RoundedCornerShape(16.dp),
                        color = MiyaSurface,
                        modifier = Modifier.size(64.dp),
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(
                                Icons.Filled.PhotoLibrary, "相册",
                                tint = MiyaAccent, modifier = Modifier.size(28.dp),
                            )
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    Text("相册", color = MiyaTextSecondary, fontSize = 12.sp)
                }
            }

            Spacer(Modifier.height(8.dp))

            TextButton(
                onClick = onDismiss,
                modifier = Modifier.align(Alignment.CenterHorizontally),
            ) {
                Text("取消", color = MiyaTextSecondary)
            }
        }
    }
}
