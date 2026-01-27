#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> mistakes(n + 2, 0);
    string s;
    for (int t = 0; t < m; ++t) {
        cin >> s;
        vector<int> g(n + 2);
        for (int i = 0; i < n; ++i) g[i] = s[i] - '0';
        g[n] = 0; // constant expert 0
        g[n + 1] = 1; // constant expert 1
        
        int best = 0;
        for (int i = 1; i < n + 2; ++i) {
            if (mistakes[i] < mistakes[best]) best = i;
        }
        int myGuess = g[best];
        cout << myGuess << '\n' << flush;
        
        char outcome_char;
        cin >> outcome_char;
        int outcome = outcome_char - '0';
        for (int i = 0; i < n + 2; ++i) {
            if (g[i] != outcome) mistakes[i]++;
        }
    }
    return 0;
}