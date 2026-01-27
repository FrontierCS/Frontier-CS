#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;
        vector<int> zeros;
        for (int i = 1; i <= n; ++i) {
            string s;
            cin >> s;
            bool isZero = false;
            if (s == "0" || s == "-") {
                isZero = true;
            } else {
                bool numeric = true;
                for (size_t j = 0; j < s.size(); ++j) {
                    if (!( (j == 0 && (s[j] == '-' || isdigit(static_cast<unsigned char>(s[j])))) 
                        || (j > 0 && isdigit(static_cast<unsigned char>(s[j]))))) {
                        numeric = false;
                        break;
                    }
                }
                if (numeric) {
                    long long val = stoll(s);
                    if (val == 0) isZero = true;
                }
            }
            if (isZero) zeros.push_back(i);
        }
        cout << zeros.size();
        for (int idx : zeros) cout << " " << idx;
        if (t) cout << "\n";
    }
    return 0;
}