package com.aureum.stocks.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import coil.compose.rememberAsyncImagePainter
import coil.request.ImageRequest
import com.aureum.stocks.data.remote.ApiClient
import com.aureum.stocks.data.remote.StockResult
import com.aureum.stocks.i18n.LanguageManager
import com.aureum.stocks.ui.StockViewModel
import com.aureum.stocks.ui.StockViewModelFactory
import com.aureum.stocks.ui.components.T
import com.aureum.stocks.ui.viewmodels.AnalyzeViewModel
import java.text.NumberFormat
import java.util.Currency
import java.util.Locale

@Composable
fun ResultScreen(
    navController: NavController,
    viewModel: AnalyzeViewModel,
    languageViewModel: com.aureum.stocks.ui.LanguageViewModel = viewModel()
) {
    val languageState by languageViewModel.language.collectAsState()
    val uiState by viewModel.uiState.collectAsState()
    
    val stockViewModel: StockViewModel = viewModel(
        factory = StockViewModelFactory(ApiClient.api)
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0A0A0A))
            .statusBarsPadding()
            .padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Spacer(modifier = Modifier.height(10.dp))

        T(
            "portfolio_analysis",
            style = MaterialTheme.typography.titleSmall.copy(
                letterSpacing = 4.sp,
                fontWeight = FontWeight.Bold
            ),
            color = Color.Gray,
            currentLang = languageState
        )

        Box(modifier = Modifier.weight(1f)) {
            if (uiState.loading) {
                Column(
                    modifier = Modifier.align(Alignment.Center),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    CircularProgressIndicator(color = Color.White)
                    Spacer(modifier = Modifier.height(16.dp))
                    T(
                        uiState.loadingMessage,
                        style = MaterialTheme.typography.bodyLarge.copy(
                            color = Color.Gray,
                            fontSize = 18.sp
                        ),
                        textAlign = TextAlign.Center,
                        currentLang = languageState
                    )
                }
            } else if (uiState.error != null) {
                T(
                    uiState.error!!,
                    style = MaterialTheme.typography.bodyLarge.copy(
                        fontSize = 18.sp
                    ),
                    color = Color(0xFFFFB4AB),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.align(Alignment.Center).padding(32.dp),
                    currentLang = languageState
                )
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                    contentPadding = PaddingValues(bottom = 20.dp)
                ) {
                    items(uiState.results, key = { it.symbol }) { stock ->
                        StockCard(stock = stock, viewModel = stockViewModel, currentLang = languageState)
                    }
                }
            }
        }

        Button(
            onClick = {
                viewModel.resetResults()
                navController.popBackStack()
            },
            modifier = Modifier.fillMaxWidth().height(56.dp).padding(bottom = 8.dp),
            shape = RoundedCornerShape(28.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color.White, contentColor = Color.Black)
        ) {
            T("new_query", fontWeight = FontWeight.Bold, currentLang = languageState)
        }
    }
}

@Composable
fun StockCard(stock: StockResult, viewModel: StockViewModel, currentLang: String) {
    var fetchedSector by remember(stock.sector) { mutableStateOf(stock.sector) }
    var fetchedIndustry by remember(stock.industry) { mutableStateOf(stock.industry) }

    LaunchedEffect(stock.symbol) {
        if (fetchedSector == null || fetchedIndustry == null) {
            kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                try {
                    val url = java.net.URL("https://finance.yahoo.com/quote/${stock.symbol}")
                    val connection = url.openConnection() as java.net.HttpURLConnection
                    connection.setRequestProperty("User-Agent", "Mozilla/5.0")
                    connection.connectTimeout = 5000
                    connection.readTimeout = 5000
                    val html = connection.inputStream.bufferedReader().use { it.readText() }
                    
                    val sectorMatch = """"sector":"([^"]+)"""".toRegex().find(html)
                    val industryMatch = """"industry":"([^"]+)"""".toRegex().find(html)
                    
                    if (sectorMatch != null) fetchedSector = sectorMatch.groupValues[1]
                    if (industryMatch != null) fetchedIndustry = industryMatch.groupValues[1]
                } catch (e: Exception) {
                    // Ignore
                }
            }
        }
    }

    val usdFormatter = remember { 
        NumberFormat.getCurrencyInstance(Locale.US).apply { 
            minimumFractionDigits = 2 
            maximumFractionDigits = 2 
        } 
    }

    val identityColor = remember(stock.symbol) {
        val hash = stock.symbol.hashCode()
        Color(
            red = (hash shr 16 and 0xFF).coerceIn(100, 255) / 255f,
            green = (hash shr 8 and 0xFF).coerceIn(100, 255) / 255f,
            blue = (hash and 0xFF).coerceIn(100, 255) / 255f
        )
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF121212)),
        border = androidx.compose.foundation.BorderStroke(0.5.dp, Color.White.copy(alpha = 0.1f))
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .clip(CircleShape)
                        .background(identityColor.copy(alpha = 0.1f))
                        .border(1.5.dp, identityColor.copy(alpha = 0.4f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    if (!stock.logo.isNullOrBlank()) {
                        Image(
                            painter = rememberAsyncImagePainter(
                                ImageRequest.Builder(LocalContext.current)
                                    .data(stock.logo)
                                    .crossfade(true)
                                    .build()
                            ),
                            contentDescription = null,
                            modifier = Modifier.size(36.dp)
                        )
                    } else {
                        Text(
                            text = stock.symbol.take(1),
                            color = identityColor,
                            fontWeight = FontWeight.Black,
                            fontSize = 24.sp
                        )
                    }
                }

                Spacer(modifier = Modifier.width(16.dp))

                Column {
                    Text(
                        text = stock.symbol,
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.ExtraBold,
                        color = Color.White
                    )
                    
                    val categoryInfo = remember(fetchedSector, fetchedIndustry) {
                        val s = fetchedSector?.trim()?.takeIf { it.isNotBlank() && it.lowercase() != "null" }
                        val i = fetchedIndustry?.trim()?.takeIf { it.isNotBlank() && it.lowercase() != "null" }
                        
                        if (s == null && i == null) {
                            LanguageManager.t("financial_asset", currentLang).uppercase()
                        } else {
                            listOfNotNull(s, i)
                                .joinToString(" • ")
                                .uppercase()
                        }
                    }

                    Text(
                        text = categoryInfo,
                        style = MaterialTheme.typography.labelMedium.copy(
                            letterSpacing = 1.2.sp
                        ),
                        color = identityColor,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = if ((stock.price_usd ?: 0.0) > 0) usdFormatter.format(stock.price_usd) else "N/A",
                style = MaterialTheme.typography.displaySmall.copy(
                    fontWeight = FontWeight.Black, 
                    fontSize = 36.sp,
                    letterSpacing = (-1).sp
                ),
                color = Color.White
            )

            Row(verticalAlignment = Alignment.CenterVertically) {
                T("aureum_score", style = MaterialTheme.typography.labelSmall, color = Color.Gray, currentLang = currentLang)
                Text(
                    text = ": " + String.format(Locale.US, "%.2f", stock.total ?: 0.0),
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Black
                )
            }

            HorizontalDivider(modifier = Modifier.padding(vertical = 16.dp), color = Color.White.copy(alpha = 0.05f))

            PriceSection(stock = stock, viewModel = viewModel, currentLang = currentLang)

            Spacer(modifier = Modifier.height(20.dp))
            Text(
                text = LanguageManager.t("precision_metrics", currentLang),
                style = MaterialTheme.typography.labelSmall,
                color = Color.Gray,
                modifier = Modifier.padding(bottom = 12.dp)
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                val indicators = listOf(
                    LanguageManager.t("growth", currentLang) to (stock.ia1 ?: 0.0),
                    LanguageManager.t("valuation", currentLang) to (stock.ia2 ?: 0.0),
                    LanguageManager.t("solvency", currentLang) to (stock.ia3 ?: 0.0),
                    LanguageManager.t("profitability", currentLang) to (stock.ia4 ?: 0.0),
                    LanguageManager.t("trend", currentLang) to (stock.ia5 ?: 0.0),
                    LanguageManager.t("risk", currentLang) to (stock.ia6 ?: 0.0)
                )

                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    indicators.take(3).forEach { (label, value) ->
                        IndicatorRow(label, value)
                    }
                }
                Spacer(modifier = Modifier.width(16.dp))
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    indicators.drop(3).forEach { (label, value) ->
                        IndicatorRow(label, value)
                    }
                }
            }

            stock.summary?.takeIf { it.isNotEmpty() }?.let { summaryList ->
                Spacer(modifier = Modifier.height(16.dp))
                val iconLabels = listOf("📈", "⚖️", "⚠️", "🏦", "🧠", "🏢")
                
                summaryList.forEachIndexed { index, info ->
                    Row(modifier = Modifier.padding(vertical = 6.dp)) {
                        Text(
                            text = "${iconLabels.getOrNull(index) ?: "•"} ",
                            color = MaterialTheme.colorScheme.primary,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = info.trim(),
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color.LightGray,
                            lineHeight = 20.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun PriceSection(stock: StockResult, viewModel: StockViewModel, currentLang: String) {
    val selectedCurrency by viewModel.selectedCurrency.collectAsState()
    val currentRate by viewModel.currentRate.collectAsState()
    val isConverting by viewModel.isConverting.collectAsState()
    var expanded by remember { mutableStateOf(false) }

    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Column {
            T("usd_quote", style = MaterialTheme.typography.labelSmall, color = Color.Gray, currentLang = currentLang)
            Text(
                text = String.format(Locale.US, "$ %.2f", stock.price_usd ?: 0.0),
                style = MaterialTheme.typography.bodyLarge, color = Color.White, fontWeight = FontWeight.SemiBold
            )
        }

        Column(horizontalAlignment = Alignment.End) {
            T(text = "convert_to", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary, currentLang = currentLang)
            Spacer(modifier = Modifier.height(4.dp))
            Box {
                Row(
                    modifier = Modifier
                        .clickable { expanded = true }
                        .background(Color.White.copy(alpha = 0.1f), RoundedCornerShape(8.dp))
                        .padding(horizontal = 8.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(selectedCurrency, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    if (isConverting) {
                        CircularProgressIndicator(modifier = Modifier.padding(start = 4.dp).size(12.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.primary)
                    } else {
                        Icon(Icons.Default.ArrowDropDown, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                    }
                }

                DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }, modifier = Modifier.background(Color(0xFF1A1A1A))) {
                    listOf("USD", "EUR", "ARS", "BRL", "MXN", "CLP").forEach { curr ->
                        DropdownMenuItem(
                            text = { Text(curr, color = Color.White) },
                            onClick = {
                                expanded = false
                                viewModel.convertPrice(curr)
                            }
                        )
                    }
                }
            }

            val basePrice = stock.price_usd ?: 0.0
            val convertedPrice = if (selectedCurrency == "USD") basePrice else (basePrice * currentRate)
            
            val formattedPrice = try {
                val format = NumberFormat.getCurrencyInstance()
                format.currency = Currency.getInstance(selectedCurrency)
                format.format(convertedPrice)
            } catch (e: Exception) {
                val format = NumberFormat.getCurrencyInstance(Locale.US)
                val symbol = when(selectedCurrency) {
                    "ARS" -> "$"
                    "EUR" -> "€"
                    "MXN" -> "MX$"
                    else -> selectedCurrency
                }
                "$symbol " + format.format(convertedPrice).substring(1)
            }

            Text(
                text = formattedPrice,
                style = MaterialTheme.typography.bodyLarge,
                color = if (isConverting) Color.Gray else MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Black
            )
        }
    }
}

@Composable
fun IndicatorRow(label: String, value: Double) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = label.uppercase(),
                style = MaterialTheme.typography.labelSmall,
                color = Color.White.copy(alpha = 0.7f),
                fontWeight = FontWeight.Bold
            )
            Text(
                text = String.format(Locale.US, "%.2f", value),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Black
            )
        }
        Spacer(modifier = Modifier.height(4.dp))
        LinearProgressIndicator(
            progress = { value.toFloat().coerceIn(0f, 1f) },
            modifier = Modifier
                .fillMaxWidth()
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp)),
            color = MaterialTheme.colorScheme.primary,
            trackColor = Color.White.copy(alpha = 0.05f),
        )
    }
}
