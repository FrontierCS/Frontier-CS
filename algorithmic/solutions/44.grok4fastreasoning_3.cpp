#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N;
    cin >> N;
    vector<long long> X(N), Y(N);
    for(int i = 0; i < N; i++) {
        cin >> X[i] >> Y[i];
    }
    vector<bool> is_prime(N, true);
    is_prime[0] = is_prime[1] = false;
    for(long long i = 2; i * i < N; i++) {
        if(is_prime[i]) {
            for(long long j = i * i; j < N; j += i) {
                is_prime[j] = false;
            }
        }
    }
    auto dist = [&](int a, int b) -> double {
        long long dx = X[a] - X[b];
        long long dy = Y[a] - Y[b];
        return sqrt(dx * dx + dy * dy);
    };
    // Forward path
    vector<int> fwd_path(N + 1);
    fwd_path[0] = 0;
    for(int i = 1; i < N; i++) fwd_path[i] = i;
    fwd_path[N] = 0;
    double L_fwd = 0.0;
    for(int i = 0; i < N; i++) {
        int a = fwd_path[i];
        int b = fwd_path[i + 1];
        int t = i + 1;
        double m = 1.0;
        if(t % 10 == 0 && !is_prime[a]) m = 1.1;
        L_fwd += m * dist(a, b);
    }
    // Reverse path
    vector<int> rev_path(N + 1);
    rev_path[0] = 0;
    for(int i = 1; i < N; i++) {
        rev_path[i] = N - i;
    }
    rev_path[N] = 0;
    double L_rev = 0.0;
    for(int i = 0; i < N; i++) {
        int a = rev_path[i];
        int b = rev_path[i + 1];
        int t = i + 1;
        double m = 1.0;
        if(t % 10 == 0 && !is_prime[a]) m = 1.1;
        L_rev += m * dist(a, b);
    }
    // Choose the better one
    vector<int> chosen_path;
    if(L_fwd <= L_rev) {
        chosen_path = fwd_path;
    } else {
        chosen_path = rev_path;
    }
    cout << N + 1 << '\n';
    for(int city : chosen_path) {
        cout << city << '\n';
    }
    return 0;
}