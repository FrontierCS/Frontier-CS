#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long N;
    if (!(cin >> N)) return 0;
    for (long long i = 1; i <= N; ++i) {
        cout << "! " << (2*i - 1) << " " << (2*i) << "\n";
        cout.flush();
    }
    return 0;
}