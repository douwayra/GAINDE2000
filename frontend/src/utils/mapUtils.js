// Utility to clean country names and get coordinates for map visualization

export const countryNameMap = {
  'SÉNÉGAL': 'Senegal',
  'SENEGAL': 'Senegal',
  'SENGAL': 'Senegal',
  'CHINE': 'China',
  'CHINZ': 'China',
  'CHINA': 'China',
  'FRANCE': 'France',
  'INDE': 'India',
  'INDIA': 'India',
  'MALI': 'Mali',
  'CÔTE D\'IVOIRE': "Côte d'Ivoire",
  'COTE D\'IVOIRE': "Côte d'Ivoire",
  'COTE D\' IVOIRE': "Côte d'Ivoire",
  'COTED\'IVOIR': "Côte d'Ivoire",
  'COTE DIVOIRE': "Côte d'Ivoire",
  'COTE D IVOIRE': "Côte d'Ivoire",
  'GUINÉE': 'Guinea',
  'GUINEE': 'Guinea',
  'BURKINA FASO': 'Burkina Faso',
  'BURKINA': 'Burkina Faso',
  'BOURKINA': 'Burkina Faso',
  'NIGER': 'Niger',
  'BÉNIN': 'Benin',
  'BENIN': 'Benin',
  'TOGO': 'Togo',
  'GHANA': 'Ghana',
  'NIGERIA': 'Nigeria',
  'GAMBIE': 'Gambia',
  'GAMBIA': 'Gambia',
  'CAP-VERT': 'Cape Verde',
  'GUINÉE-BISSAU': 'Guinea-Bissau',
  'LIBERIA': 'Liberia',
  'SIERRA LEONE': 'Sierra Leone',
  'SIERRA-LEONE': 'Sierra Leone',
  'PAYS-BAS': 'Netherlands',
  'NETHERLANDS': 'Netherlands',
  'BELGIQUE': 'Belgium',
  'BELGIUM': 'Belgium',
  'ALLEMAGNE': 'Germany',
  'GERMANY': 'Germany',
  'ITALIE': 'Italy',
  'ITALY': 'Italy',
  'ESPAGNE': 'Spain',
  'SPAIN': 'Spain',
  'ROYAUME-UNI': 'United Kingdom',
  'UNITED KINGDOM': 'United Kingdom',
  'SUISSE': 'Switzerland',
  'SWITZERLAND': 'Switzerland',
  'PORTUGAL': 'Portugal',
  'SUÈDE': 'Sweden',
  'SWEDEN': 'Sweden',
  'POLOGNE': 'Poland',
  'POLAND': 'Poland',
  'AUTRICHE': 'Austria',
  'DANEMARK': 'Denmark',
  'FINLANDE': 'Finland',
  'IRLANDE': 'Ireland',
  'GRÈCE': 'Greece',
  'NORVÈGE': 'Norway',
  'HONGRIE': 'Hungary',
  'ROUMANIE': 'Romania',
  'TURQUIE': 'Turkey',
  'TURKEY': 'Turkey',
  'JAPON': 'Japan',
  'JAPAN': 'Japan',
  'ÉMIRATS ARABES UNIS': 'United Arab Emirates',
  'EMIRATS ARABES UNIS': 'United Arab Emirates',
  'EMIRATS ARABES': 'United Arab Emirates',
  'ARABIE SAOUDITE': 'Saudi Arabia',
  'INDONÉSIE': 'Indonesia',
  'CORÉE DU SUD': 'South Korea',
  'THAÏLANDE': 'Thailand',
  'VIETNAM': 'Vietnam',
  'MALAISIE': 'Malaysia',
  'SINGAPOUR': 'Singapore',
  'PAKISTAN': 'Pakistan',
  'BANGLADESH': 'Bangladesh',
  'IRAN': 'Iran',
  'IRAK': 'Iraq',
  'LIBAN': 'Lebanon',
  'KOWEÏT': 'Kuwait',
  'ÉTATS-UNIS': 'United States',
  'ÉTATS-UNIS D\'AMÉRIQUE': 'United States',
  'ETATS UNIS': 'United States',
  'E TATS-UNIS': 'United States',
  'CANADA': 'Canada',
  'BRÉSIL': 'Brazil',
  'BRAZIL': 'Brazil',
  'MAROC': 'Morocco',
  'ALGÉRIE': 'Algeria',
  'TUNISIE': 'Tunisia',
  'ÉGYPTE': 'Egypt',
  'AFRIQUE DU SUD': 'South Africa',
  'SOUTH AFRICA': 'South Africa'
};

export const countryCoords = {
  'China': [104.19, 35.86],
  'France': [2.21, 46.22],
  'India': [78.96, 20.59],
  'Netherlands': [5.29, 52.13],
  'Spain': [-3.74, 40.46],
  'United States': [-95.71, 37.09],
  'Mali': [-3.99, 17.57],
  'Belgium': [4.46, 50.50],
  'United Arab Emirates': [53.84, 23.42],
  'Germany': [10.45, 51.16],
  'Turkey': [35.24, 38.96],
  'Japan': [138.25, 36.20],
  'Saudi Arabia': [45.07, 23.88],
  'Indonesia': [113.92, -0.78],
  'South Korea': [127.76, 35.90],
  'Thailand': [100.99, 15.87],
  'Vietnam': [108.27, 14.05],
  'Malaysia': [101.97, 4.21],
  'Singapore': [103.81, 1.35],
  'Pakistan': [69.34, 30.37],
  'Bangladesh': [90.35, 23.68],
  'Brazil': [-51.92, -14.23],
  'Canada': [-106.34, 56.13],
  'Morocco': [-7.09, 31.79],
  'Algeria': [1.65, 28.03],
  'Tunisia': [9.53, 33.88],
  'Egypt': [30.80, 26.82],
  'South Africa': [25.04, -28.47],
  'Guinea': [-9.69, 9.94],
  'Burkina Faso': [-1.56, 12.23],
  'Niger': [8.08, 17.60],
  'Benin': [2.31, 9.30],
  'Togo': [0.82, 8.61],
  'Ghana': [-1.02, 7.94],
  'Nigeria': [8.67, 9.08],
  'Gambia': [-15.31, 13.44],
  'Cape Verde': [-23.04, 16.00],
  'Guinea-Bissau': [-15.18, 11.80],
  'Liberia': [-9.42, 6.42],
  'Sierra Leone': [-11.77, 8.46],
  'United Kingdom': [-1.17, 54.23],
  'Switzerland': [8.22, 46.81],
  'Portugal': [-8.22, 39.39],
  'Sweden': [18.64, 60.12],
  'Poland': [19.14, 51.91],
  'Senegal': [-14.45, 14.49]
};

export function getStandardCountryName(rawName) {
  if (!rawName) return '';
  
  // Clean special characters, trailing spaces, parenthesized suffixes (e.g. "MADRID (ESPAGNE)")
  let name = rawName.trim().toUpperCase();
  
  // If it's a compound format like "Rotterdam-Pays-Bas", extract the country part
  if (name.includes('-')) {
    const parts = name.split('-');
    // Check if any part matches our dictionary
    for (const part of parts) {
      const cleanedPart = part.trim();
      if (countryNameMap[cleanedPart]) {
        return countryNameMap[cleanedPart];
      }
    }
  }
  
  // Look for sub-strings to catch names like "SHENZHEN / CHINE" or "MADRID (ESPAGNE)"
  for (const key of Object.keys(countryNameMap)) {
    if (name.includes(key)) {
      return countryNameMap[key];
    }
  }

  // Fallback to title case
  return rawName.charAt(0).toUpperCase() + rawName.slice(1).toLowerCase();
}
