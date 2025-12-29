#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long T;
    if (!(cin >> N >> T)) return 0;

    string row;
    for (int i = 0; i < N; ++i) {
        cin >> row; // read and ignore
    }

    // Output zero moves (empty line)
    cout << '\n';
    return 0;
}