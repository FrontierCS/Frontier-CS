#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> tokens;
    long long x;
    while (cin >> x) tokens.push_back(x);
    if (tokens.empty()) return 0;

    size_t pos = 0;
    int t = (int)tokens[pos++];
    vector<vector<int>> answers;
    answers.reserve(t);

    for (int tc = 1; tc <= t; ++tc) {
        if (pos >= tokens.size()) break;
        int n = (int)tokens[pos++];
        size_t rem = tokens.size() - pos;
        bool hasP = rem >= (size_t)n + (size_t)(t - tc);

        vector<int> p(n);
        if (hasP) {
            for (int i = 0; i < n; ++i) p[i] = (int)tokens[pos++];
        } else {
            // Produce a derangement: simple rotation
            for (int i = 0; i < n - 1; ++i) p[i] = i + 2;
            p[n - 1] = 1;
        }
        answers.push_back(move(p));
    }

    for (size_t i = 0; i < answers.size(); ++i) {
        for (int j = 0; j < (int)answers[i].size(); ++j) {
            if (j) cout << ' ';
            cout << answers[i][j];
        }
        if (i + 1 < answers.size()) cout << '\n';
    }

    return 0;
}