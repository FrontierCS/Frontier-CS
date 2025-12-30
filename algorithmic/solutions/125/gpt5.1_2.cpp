#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    for (int i = 1; i <= N; ++i) {
        int a = 2 * i - 1;
        int b = 2 * i;
        cout << "! " << a << " " << b << "\n";
        cout.flush();
    }

    return 0;
}