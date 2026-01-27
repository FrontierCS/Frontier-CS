#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; ++tc) {
        int N;
        if (!(cin >> N)) return 0;
        vector<string> words(N);
        for (int i = 0; i < N; ++i) {
            if (!(cin >> words[i])) words[i] = "";
        }
        cout << "answer";
        for (int i = 0; i < N; ++i) {
            cout << ' ' << words[i];
        }
        cout << '\n';
        cout.flush();
    }
    return 0;
}