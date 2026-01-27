#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long N;
    if (!(cin >> N)) return 0;
    for (long long i = 1; i <= N; ++i) {
        long long a = 2*i - 1;
        long long b = 2*i;
        cout << "! " << a << " " << b << "\n";
        cout.flush();
    }
    return 0;
}