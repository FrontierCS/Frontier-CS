#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long T;
    if (!(cin >> N >> T)) return 0;
    int er = -1, ec = -1;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            string s;
            cin >> s;
            if (s[0] == '0') {
                er = i;
                ec = j;
            }
        }
    }

    string ans;
    // Move empty to bottom-right corner (N-1, N-1)
    while (er < N - 1) {
        ans.push_back('D');
        ++er;
    }
    while (ec < N - 1) {
        ans.push_back('R');
        ++ec;
    }

    if ((long long)ans.size() > T) {
        // Just in case, trim (though for given constraints this won't happen)
        ans.resize(T);
    }

    cout << ans << '\n';
    return 0;
}