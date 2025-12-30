#include <bits/stdc++.h>
using namespace std;

long long do_walk(long long x) {
    cout << "walk " << x << endl;
    cout.flush();
    long long v;
    if (!(cin >> v)) exit(0);
    return v;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int MAX_WALKS = 200000;

    long long totalSteps = 0;
    long long label = do_walk(0); // initial position
    int walks = 1;

    unordered_map<long long, long long> last;
    last.reserve(200000);
    last.max_load_factor(0.7);

    last[label] = totalSteps;
    long long G = 0;
    int collisions = 0;

    mt19937_64 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<long long> dist(1, 1000000000LL);

    while (walks < MAX_WALKS) {
        long long x = dist(rng);
        label = do_walk(x);
        walks++;
        totalSteps += x;

        auto it = last.find(label);
        if (it == last.end()) {
            last[label] = totalSteps;
        } else {
            long long delta = totalSteps - it->second;
            it->second = totalSteps;
            if (delta > 0) {
                if (G == 0) G = delta;
                else G = std::gcd(G, delta);
                collisions++;
            }
        }
    }

    if (G == 0) G = 1;
    if (G > 1000000000LL) {
        // Clamp to constraint range; n is at most 1e9
        G = 1000000000LL;
    }

    cout << "guess " << G << endl;
    cout.flush();

    return 0;
}