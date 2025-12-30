#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <set>

using namespace std;

double dist(int a, int b, const vector<long long>& x, const vector<long long>& y) {
    long long dx = x[a] - x[b];
    long long dy = y[a] - y[b];
    return sqrt(dx*dx + dy*dy);
}

vector<int> affected_edges(int i, int j, int N) {
    // assumes i < j, N cities, Q length = N-1
    set<int> edges;
    // edge for left of i
    if (i == 0) edges.insert(0);
    else edges.insert(i);          // edge i connects Q[i-1] to Q[i]
    // edge for right of i
    if (i == N-2) edges.insert(N-1);
    else edges.insert(i+1);
    // edge for left of j
    if (j == 0) edges.insert(0);
    else edges.insert(j);
    // edge for right of j
    if (j == N-2) edges.insert(N-1);
    else edges.insert(j+1);
    return vector<int>(edges.begin(), edges.end());
}

double compute_delta(int i, int j, const vector<int>& Q, const vector<double>& D,
                     const vector<long long>& x, const vector<long long>& y,
                     const vector<bool>& is_prime, int N) {
    if (i > j) swap(i, j);
    vector<int> affected = affected_edges(i, j, N);
    double delta = 0.0;
    for (int e : affected) {
        // old contribution
        double old_dist = D[e];
        int old_source = (e == 0) ? 0 : Q[e-1];
        bool old_prime = is_prime[old_source];
        double old_mult = ((e+1) % 10 == 0 && !old_prime) ? 1.1 : 1.0;
        // new cities after swap
        int city1, city2;
        if (e == 0) {
            city1 = 0;
            int k = 0;
            int new_Qk = (k == i) ? Q[j] : (k == j) ? Q[i] : Q[k];
            city2 = new_Qk;
        } else if (e == N-1) {
            int k = N-2;
            int new_Qk = (k == i) ? Q[j] : (k == j) ? Q[i] : Q[k];
            city1 = new_Qk;
            city2 = 0;
        } else {
            int k1 = e-1, k2 = e;
            int new_Qk1 = (k1 == i) ? Q[j] : (k1 == j) ? Q[i] : Q[k1];
            int new_Qk2 = (k2 == i) ? Q[j] : (k2 == j) ? Q[i] : Q[k2];
            city1 = new_Qk1;
            city2 = new_Qk2;
        }
        double new_dist = dist(city1, city2, x, y);
        int new_source = (e == 0) ? 0 : ( (e-1 == i) ? Q[j] : (e-1 == j) ? Q[i] : Q[e-1] );
        bool new_prime = is_prime[new_source];
        double new_mult = ((e+1) % 10 == 0 && !new_prime) ? 1.1 : 1.0;
        delta += new_mult * new_dist - old_mult * old_dist;
    }
    return delta;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<long long> x(N), y(N);
    for (int i = 0; i < N; ++i) {
        cin >> x[i] >> y[i];
    }

    // sieve for primes up to N-1
    vector<bool> is_prime(N, false);
    if (N > 2) is_prime[2] = true;
    for (int i = 3; i < N; ++i) is_prime[i] = true;
    for (int i = 2; i < N; ++i) {
        if (is_prime[i]) {
            for (int j = i+i; j < N; j += i) {
                is_prime[j] = false;
            }
        }
    }
    is_prime[0] = is_prime[1] = false;

    // baseline Q = [1,2,...,N-1]
    vector<int> Q(N-1);
    for (int i = 1; i < N; ++i) {
        Q[i-1] = i;
    }

    // compute initial edge distances
    vector<double> D(N); // edges 0..N-1
    D[0] = dist(0, Q[0], x, y);
    for (int i = 1; i <= N-2; ++i) {
        D[i] = dist(Q[i-1], Q[i], x, y);
    }
    D[N-1] = dist(Q[N-2], 0, x, y);

    // penalty indices in Q
    vector<int> penalty_indices;
    for (int t = 10; t <= N; t += 10) {
        int idx = t - 2;
        if (idx <= N-2) {
            penalty_indices.push_back(idx);
        }
    }

    const int WINDOW = 100;
    vector<bool> fixed(N-1, false);

    for (int i : penalty_indices) {
        if (is_prime[Q[i]]) {
            fixed[i] = true;
            continue;
        }
        int best_j = -1;
        double best_delta = 0.0;
        int left = max(0, i - WINDOW);
        int right = min(N-2, i + WINDOW);
        for (int j = left; j <= right; ++j) {
            if (j == i) continue;
            if (!is_prime[Q[j]]) continue;
            if (fixed[j]) continue;
            double delta = compute_delta(i, j, Q, D, x, y, is_prime, N);
            if (best_j == -1 || delta < best_delta) {
                best_delta = delta;
                best_j = j;
            }
        }
        if (best_j != -1) {
            // perform swap
            swap(Q[i], Q[best_j]);
            // update D for affected edges
            vector<int> affected = affected_edges(i, best_j, N);
            for (int e : affected) {
                if (e == 0) {
                    D[e] = dist(0, Q[0], x, y);
                } else if (e == N-1) {
                    D[e] = dist(Q[N-2], 0, x, y);
                } else {
                    D[e] = dist(Q[e-1], Q[e], x, y);
                }
            }
            fixed[i] = true;
        }
    }

    // output
    cout << N+1 << "\n";
    cout << 0 << "\n";
    for (int i = 0; i < N-1; ++i) {
        cout << Q[i] << "\n";
    }
    cout << 0 << "\n";

    return 0;
}