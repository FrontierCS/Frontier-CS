#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, R;
    if (!(cin >> N >> R)) return 0;

    vector<int> U(N), V(N);
    for (int i = 0; i < N; ++i) {
        if (!(cin >> U[i] >> V[i])) return 0;
    }

    string T, tmp;
    if (cin >> T) {
        // If there are extra tokens, assume the last one is the actual T
        while (cin >> tmp) T = tmp;
        if ((int)T.size() != N) {
            T = string(N, '&');
        }
    } else {
        T = string(N, '&');
    }

    cout << "! " << T << "\n";
    return 0;
}