#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    for (int i = 1; i <= 2 * N; i += 2) {
        cout << "! " << i << " " << (i + 1) << "\n";
        cout.flush();
    }

    return 0;
}