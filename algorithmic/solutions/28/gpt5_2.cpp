#include <bits/stdc++.h>
using namespace std;

bool isLowercaseWord(const string& s) {
    if (s.empty() || s.size() > 10) return false;
    for (char c : s) {
        if (c < 'a' || c > 'z') return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; ++tc) {
        int N;
        if (!(cin >> N)) break;
        unordered_set<string> seen;
        vector<string> words;
        words.reserve(N);
        string token;
        while ((int)seen.size() < N && (cin >> token)) {
            if (isLowercaseWord(token)) {
                if (seen.insert(token).second) {
                    words.push_back(token);
                }
            }
        }
        sort(words.begin(), words.end());
        cout << "answer";
        for (auto &w : words) {
            cout << ' ' << w;
        }
        cout << '\n';
    }
    return 0;
}