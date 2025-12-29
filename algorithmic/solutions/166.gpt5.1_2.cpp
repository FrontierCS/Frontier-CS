#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<int> h(N * N);
    for (int i = 0; i < N * N; i++) cin >> h[i];

    // Output no operations (T = 0 implicitly)
    return 0;
}