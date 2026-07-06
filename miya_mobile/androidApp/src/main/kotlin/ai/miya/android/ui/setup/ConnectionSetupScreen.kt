package ai.miya.android.ui.setup

import ai.miya.android.ui.theme.LocalMiyaColors
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun ConnectionSetupScreen(
    onConnected: (host: String, port: Int) -> Unit,
) {
    val colors = LocalMiyaColors.current
    var host by remember { mutableStateOf("") }
    var port by remember { mutableStateOf("8000") }
    var isLoading by remember { mutableStateOf(false) }
    var errorMsg by remember { mutableStateOf<String?>(null) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(colors.background)
            .systemBarsPadding()
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Spacer(Modifier.weight(1f))

            Box(
                modifier = Modifier
                    .size(80.dp)
                    .clip(CircleShape)
                    .background(colors.primary.copy(alpha = 0.12f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = "弥",
                    color = colors.primary,
                    fontSize = 36.sp,
                    fontWeight = FontWeight.Bold,
                )
            }

            Spacer(Modifier.height(20.dp))

            Text(
                text = "弥娅",
                color = colors.textPrimary,
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
            )

            Text(
                text = "MIYA AI Companion",
                color = colors.textSecondary,
                fontSize = 13.sp,
                fontFamily = FontFamily.Monospace,
                letterSpacing = 2.sp,
            )

            Spacer(Modifier.height(8.dp))

            Text(
                text = "连接到运行在电脑上的弥娅服务",
                color = colors.textDim,
                fontSize = 13.sp,
            )

            Spacer(Modifier.height(40.dp))

            OutlinedTextField(
                value = host,
                onValueChange = { host = it; errorMsg = null },
                label = { Text("服务器地址") },
                placeholder = { Text("例如: 192.168.1.100", color = colors.textDim) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = colors.surface,
                    unfocusedContainerColor = colors.surface,
                    focusedBorderColor = colors.primary,
                    unfocusedBorderColor = colors.borderDim,
                    focusedTextColor = colors.textPrimary,
                    unfocusedTextColor = colors.textPrimary,
                    cursorColor = colors.accent,
                    focusedLabelColor = colors.primary,
                    unfocusedLabelColor = colors.textSecondary,
                ),
                shape = RoundedCornerShape(12.dp),
            )

            Spacer(Modifier.height(12.dp))

            OutlinedTextField(
                value = port,
                onValueChange = { port = it; errorMsg = null },
                label = { Text("端口") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = colors.surface,
                    unfocusedContainerColor = colors.surface,
                    focusedBorderColor = colors.primary,
                    unfocusedBorderColor = colors.borderDim,
                    focusedTextColor = colors.textPrimary,
                    unfocusedTextColor = colors.textPrimary,
                    cursorColor = colors.accent,
                    focusedLabelColor = colors.primary,
                    unfocusedLabelColor = colors.textSecondary,
                ),
                shape = RoundedCornerShape(12.dp),
            )

            AnimatedVisibility(visible = errorMsg != null) {
                Text(
                    text = errorMsg ?: "",
                    color = colors.danger,
                    fontSize = 12.sp,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }

            Spacer(Modifier.height(24.dp))

            Button(
                onClick = {
                    val hostTrimmed = host.trim()
                    if (hostTrimmed.isEmpty()) {
                        errorMsg = "请输入服务器地址"
                        return@Button
                    }
                    val portNum = port.trim().toIntOrNull()
                    if (portNum == null || portNum !in 1..65535) {
                        errorMsg = "请输入有效端口 (1-65535)"
                        return@Button
                    }
                    isLoading = true
                    onConnected(hostTrimmed, portNum)
                },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                enabled = !isLoading,
                colors = ButtonDefaults.buttonColors(containerColor = colors.primary),
                shape = RoundedCornerShape(12.dp),
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = colors.surface,
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text("连接弥娅", fontSize = 16.sp, fontWeight = FontWeight.Medium)
                }
            }

            Spacer(Modifier.height(12.dp))

            Text(
                text = "手机和电脑需在同一局域网\n或通过 frp/ngrok 远程访问",
                color = colors.textDim,
                fontSize = 11.sp,
                textAlign = TextAlign.Center,
                lineHeight = 16.sp,
            )

            Spacer(Modifier.weight(1f))
        }
    }
}
