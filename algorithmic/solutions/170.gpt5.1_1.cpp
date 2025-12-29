#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long L;
    if (!(cin >> N >> L)) return 0;
    vector<int> T(N);
    for (int i = 0; i < N; ++i) cin >> T[i];

    for (int i = 0; i < N; ++i) {
        int nxt = (i + 1) % N;
        cout << nxt << " " << nxt << "\n";
    }
    return 0;
}