#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<int> a(11);
    for (int i = 1; i <= 10; ++i) cin >> a[i];
    for (int i = 0; i < N; ++i) {
        int xi, yi;
        cin >> xi >> yi;
    }

    int k = K;
    cout << k << "\n";
    for (int i = 0; i < k; ++i) {
        long long b = 1LL * i * i;
        long long p_x = 0, p_y = b;
        long long q_x = 1, q_y = b + i;
        cout << p_x << " " << p_y << " " << q_x << " " << q_y << "\n";
    }
    return 0;
}