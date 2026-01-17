#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

long long n_val;

// This function calculates the power of a spell formed by w_u + w_v,
// where w_i = X^i O X^{n+i}.
// The spell has the form X^a O X^b O X^c, with a=u, b=u+v+n, c=v+n.
// The number of distinct substrings simplifies to the polynomial:
// u^2 + v^2 + 3uv + (3n+4)u + (2n+4)v + n^2+4n+1
long long get_power_poly(long long u, long long v) {
    long long n = n_val;
    long long u_sq = u * u;
    long long v_sq = v * v;
    long long uv3 = 3 * u * v;
    long long u_term = (3 * n + 4) * u;
    long long v_term = (2 * n + 4) * v;
    long long n_term = n * n + 4 * n + 1;
    return u_sq + v_sq + uv3 + u_term + v_term + n_term;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;
    n_val = n;

    vector<long long> L(n + 1), K(n + 1);
    for (int i = 1; i <= n; ++i) {
        L[i] = i;
        K[i] = n + i;
    }

    for (int i = 1; i <= n; ++i) {
        string w;
        w.reserve(L[i] + K[i] + 1);
        for (int j = 0; j < L[i]; ++j) w += 'X';
        w += 'O';
        for (int j = 0; j < K[i]; ++j) w += 'X';
        cout << w << '\n';
    }
    cout.flush();

    map<long long, pair<int, int>> power_map;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            power_map[get_power_poly(i, j)] = {i, j};
        }
    }

    int q;
    cin >> q;
    for (int i = 0; i < q; ++i) {
        long long p;
        cin >> p;
        pair<int, int> indices = power_map.at(p);
        cout << indices.first << " " << indices.second << '\n';
        cout.flush();
    }

    return 0;
}