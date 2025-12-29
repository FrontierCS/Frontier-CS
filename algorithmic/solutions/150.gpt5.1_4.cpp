#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    string s;
    for (int i = 0; i < M; ++i) cin >> s;

    string row(N, 'A');
    for (int i = 0; i < N; ++i) {
        cout << row << '\n';
    }
    return 0;
}