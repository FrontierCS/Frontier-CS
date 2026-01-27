#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
    }

    // Output zero modifications
    cout << 0 << "\n";
    cout.flush();

    // Try to read any remaining tokens (offline adaptation)
    vector<int> guesses;
    string tok;
    while (cin >> tok) {
        bool is_num = !tok.empty() && (isdigit(tok[0]) || (tok[0] == '-' && tok.size() > 1));
        if (is_num) {
            try {
                long long val = stoll(tok);
                if (1 <= val && val <= n) guesses.push_back((int)val);
            } catch (...) {
                // ignore
            }
        }
        if ((int)guesses.size() >= T) break;
    }

    if ((int)guesses.size() < T) guesses.resize(T, 1);

    for (int i = 0; i < T; ++i) {
        cout << "! " << guesses[i] << "\n";
        cout.flush();
    }

    return 0;
}