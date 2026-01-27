#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<long long> x(N), y(N);
    for (int i = 0; i < N; ++i) {
        cin >> x[i] >> y[i];
    }

    // Build initial order using serpentine by blocks along input order (which is sorted by x)
    int B = max(1, (int)floor(sqrt((double)N)));
    struct Node { int id; long long y; int block; };
    vector<Node> nodes;
    nodes.reserve(max(0, N - 1));
    for (int id = 1; id <= N - 1; ++id) {
        nodes.push_back({id, y[id], (id - 1) / B});
    }
    sort(nodes.begin(), nodes.end(), [](const Node& a, const Node& b){
        if (a.block != b.block) return a.block < b.block;
        if ((a.block & 1) == 0) { // even block: y ascending
            if (a.y != b.y) return a.y < b.y;
            return a.id < b.id;
        } else { // odd block: y descending
            if (a.y != b.y) return a.y > b.y;
            return a.id < b.id; // tie-breaker
        }
    });

    // Prepare path P: P0 = PN = 0
    vector<int> P(N + 1);
    P[0] = 0;
    for (int i = 1; i <= N - 1; ++i) P[i] = nodes[i - 1].id;
    P[N] = 0;

    // Sieve primes up to N-1 (city IDs)
    vector<char> isPrime(N, true);
    if (N > 0) isPrime[0] = false;
    if (N > 1) isPrime[1] = false;
    for (int i = 2; 1LL * i * i < N; ++i) {
        if (isPrime[i]) {
            for (int j = i * i; j < N; j += i) isPrime[j] = false;
        }
    }

    // Build deques of positions (1..N-1) where the city at P[i] is prime
    deque<int> dqNon, dqCand;
    for (int i = 1; i <= N - 1; ++i) {
        if (isPrime[P[i]]) {
            if ((i % 10) == 9) dqCand.push_back(i);
            else dqNon.push_back(i);
        }
    }

    // Try to ensure that at positions pos where (pos % 10 == 9), P[pos] is prime
    for (int pos = 9; pos <= N - 1; pos += 10) {
        if (isPrime[P[pos]]) continue;
        while (!dqNon.empty() && dqNon.front() <= pos) dqNon.pop_front();
        while (!dqCand.empty() && dqCand.front() <= pos) dqCand.pop_front();
        if (!dqNon.empty()) {
            int j = dqNon.front(); dqNon.pop_front();
            swap(P[pos], P[j]);
        } else if (!dqCand.empty()) {
            int j = dqCand.front(); dqCand.pop_front();
            swap(P[pos], P[j]);
        } else {
            // No more prime donors available
            break;
        }
    }

    // Output
    cout << (N + 1) << '\n';
    for (int i = 0; i <= N; ++i) {
        cout << P[i] << '\n';
    }
    return 0;
}