#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<string> tokens;
    string s;
    while (cin >> s) tokens.push_back(s);
    if (tokens.empty()) return 0;

    // First token must be n
    int n;
    try {
        n = stoi(tokens[0]);
    } catch (...) {
        return 0;
    }

    vector<long long> arr;
    // Collect next n integers, ignoring non-integer tokens like '<' or '>'
    for (size_t i = 1; i < tokens.size() && (int)arr.size() < n; ++i) {
        // try to parse integer
        try {
            size_t pos = 0;
            long long val = stoll(tokens[i], &pos);
            if (pos == tokens[i].size()) {
                arr.push_back(val);
            }
        } catch (...) {
            // ignore non-integers
        }
    }

    if ((int)arr.size() < n) {
        // Fallback: if not enough numbers provided, output identity permutation
        arr.resize(n);
        for (int i = 0; i < n; ++i) arr[i] = i + 1;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << arr[i];
    }
    cout << '\n';
    return 0;
}