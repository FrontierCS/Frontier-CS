#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <map>
#include <algorithm>

using namespace std;

using ld = long double;

const long long X = 1e8; // A large coordinate value

map<int, ld> d_cache_X;
map<int, ld> d_cache_X1;

ld query_X(int k) {
    if (d_cache_X.count(k)) {
        return d_cache_X[k];
    }
    cout << "? " << X << " " << (long long)k * X << endl;
    ld dist;
    cin >> dist;
    return d_cache_X[k] = dist;
}

ld query_X1(int k) {
    if (d_cache_X1.count(k)) {
        return d_cache_X1[k];
    }
    cout << "? " << X + 1 << " " << (long long)k * (X + 1) << endl;
    ld dist;
    cin >> dist;
    return d_cache_X1[k] = dist;
}

map<int, ld> S_cache;
ld get_S(int k) {
    if (S_cache.count(k)) {
        return S_cache[k];
    }
    ld d1 = query_X(k);
    ld d2 = query_X1(k);
    return S_cache[k] = d2 - d1;
}

map<int, ld> DeltaS_cache;
ld get_DeltaS(int k) {
    if (DeltaS_cache.count(k)) {
        return DeltaS_cache[k];
    }
    return DeltaS_cache[k] = get_S(k + 1) - get_S(k);
}

vector<long long> found_a;
const ld EPS = 1e-9;

void solve_a(int L, int R) {
    if (L > R) return;

    ld delta_S_R = get_DeltaS(R);
    ld delta_S_L_minus_1 = get_DeltaS(L - 1);

    if (fabsl(delta_S_R - delta_S_L_minus_1) < EPS) {
        return;
    }
    
    if (L == R) {
        found_a.push_back(L);
        return;
    }

    int M = L + (R - L) / 2;
    solve_a(L, M);
    solve_a(M + 1, R);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout << fixed << setprecision(10);

    int N;
    cin >> N;

    solve_a(-10000, 10000);
    
    sort(found_a.begin(), found_a.end());

    vector<long long> b_sol(N);
    vector<ld> W(N);
    for(int i=0; i<N; ++i) {
        W[i] = 1.0L / sqrtl((ld)found_a[i] * found_a[i] + 1.0L);
    }
    
    auto get_J = [&](int k) {
        ld d1 = query_X(k);
        ld d2 = query_X1(k);
        return (ld)(X+1)*d1 - (ld)X*d2;
    };
    
    int k_min = -10001;
    ld J_k_min = get_J(k_min);
    
    vector<ld> J_a(N);
    for(int i=0; i<N; ++i) {
        J_a[i] = get_J(found_a[i]);
    }

    vector<ld> B(N); // B_i = b_i * W_i
    
    ld SumBW = J_k_min;
    ld two_sum_B_prefix = 0;
    
    for (int i=0; i<N; ++i) {
        B[i] = SumBW - two_sum_B_prefix - J_a[i];
        two_sum_B_prefix += 2 * B[i];
    }
    
    for(int i=0; i<N; ++i) {
        b_sol[i] = roundl(B[i] / W[i]);
    }

    cout << "! ";
    for (int i = 0; i < N; ++i) cout << found_a[i] << (i == N - 1 ? "" : " ");
    cout << " ";
    for (int i = 0; i < N; ++i) cout << b_sol[i] << (i == N - 1 ? "" : " ");
    cout << endl;

    return 0;
}