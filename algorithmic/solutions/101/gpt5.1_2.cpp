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

    string t;
    if (cin >> t) {
        cout << t;
    }

    return 0;
}