#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N;
    cin >> N;
    vector<long long> X(N), Y(N);
    for (int i = 0; i < N; i++) {
        cin >> X[i] >> Y[i];
    }
    vector<char> is_prime(N, 1);
    if (N > 0) is_prime[0] = 0;
    if (N > 1) is_prime[1] = 0;
    for (long long i = 2; i * i <= N; i++) {
        if (is_prime[i]) {
            for (long long j = i * i; j < N; j += i) {
                is_prime[j] = 0;
            }
        }
    }
    auto compute_L = [&](const vector<int>& P) -> double {
        double sum = 0.0;
        for (int t = 1; t <= N; t++) {
            int a = P[t - 1], b = P[t];
            long long dx = X[a] - X[b];
            long long dy = Y[a] - Y[b];
            double dist = sqrt((double)(dx * dx + dy * dy));
            double m = 1.0;
            if (t % 10 == 0 && !is_prime[a]) m = 1.1;
            sum += m * dist;
        }
        return sum;
    };
    // Forward
    vector<int> Pf(N + 1);
    for (int i = 0; i < N; i++) Pf[i] = i;
    Pf[N] = 0;
    double Lf = compute_L(Pf);
    // Backward
    vector<int> Pb(N + 1);
    Pb[0] = 0;
    for (int i = 1; i < N; i++) Pb[i] = N - i;
    Pb[N] = 0;
    double Lb = compute_L(Pb);
    // Option 1: forward odds, back evens
    vector<int> P1(N + 1);
    int idx1 = 0;
    P1[idx1++] = 0;
    for (int i = 1; i < N; i += 2) P1[idx1++] = i;
    int maxid = N - 1;
    int rbe = (maxid % 2 == 0) ? maxid : maxid - 1;
    for (int i = rbe; i >= 2; i -= 2) P1[idx1++] = i;
    P1[idx1++] = 0;
    double L1 = compute_L(P1);
    // Option 2: forward evens, back odds
    vector<int> P2(N + 1);
    int idx2 = 0;
    P2[idx2++] = 0;
    for (int i = 2; i < N; i += 2) P2[idx2++] = i;
    int rbo = (maxid % 2 == 1) ? maxid : maxid - 1;
    for (int i = rbo; i >= 1; i -= 2) P2[idx2++] = i;
    P2[idx2++] = 0;
    double L2 = compute_L(P2);
    // Find best
    vector<pair<double, vector<int>>> cands = {{Lf, Pf}, {Lb, Pb}, {L1, P1}, {L2, P2}};
    sort(cands.begin(), cands.end());
    vector<int> best = cands[0].second;
    cout << N + 1 << '\n';
    for (int city : best) {
        cout << city << '\n';
    }
    return 0;
}