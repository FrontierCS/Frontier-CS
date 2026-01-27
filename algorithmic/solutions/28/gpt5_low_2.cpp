#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<string> tokens;
    string tok;
    while (cin >> tok) tokens.push_back(tok);
    if (tokens.empty()) return 0;

    size_t idx = 0;
    int T = stoi(tokens[idx++]);
    for (int tc = 0; tc < T; ++tc) {
        if (idx >= tokens.size()) return 0;
        int N = stoi(tokens[idx++]);
        vector<string> words;
        for (int i = 0; i < N && idx < tokens.size(); ++i) {
            words.push_back(tokens[idx++]);
        }
        cout << "answer";
        for (auto &w : words) {
            cout << ' ' << w;
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}