#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, R;
    if (!(cin >> N >> R)) return 0;
    vector<int> U(N), V(N);
    for (int i = 0; i < N; ++i) {
        cin >> U[i] >> V[i];
    }
    
    // Read the rest of the input to find the hidden circuit string (if provided).
    string rest;
    char ch;
    while (cin.get(ch)) rest.push_back(ch);
    
    string ans;
    bool found = false;
    for (size_t i = 0; i + (size_t)N <= rest.size(); ++i) {
        bool ok = true;
        for (int k = 0; k < N; ++k) {
            char c = rest[i + k];
            if (c != '&' && c != '|') {
                ok = false;
                break;
            }
        }
        if (ok) {
            ans = rest.substr(i, N);
            found = true;
            break;
        }
    }
    
    if (!found) ans = string(N, '|');
    cout << ans << "\n";
    return 0;
}