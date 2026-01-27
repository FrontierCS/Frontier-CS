#include <bits/stdc++.h>
using namespace std;

static const int QMAX = 30000;

struct Interactor {
    int n, m;
    int N;
    int qcnt = 0;

    int query(int x, int d) {
        cout << "? " << x << " " << d << "\n";
        cout.flush();
        int a;
        if (!(cin >> a)) exit(0);
        if (a == -1) exit(0);
        qcnt++;
        return a;
    }

    void answer(const vector<int>& p) {
        cout << "!";
        for (int i = 1; i < n; i++) cout << " " << p[i];
        cout << "\n";
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Interactor it;
    cin >> it.n >> it.m;
    it.N = it.n * it.m;

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Get initial a without changing state
    int a1 = it.query(0, +1);
    int a = it.query(0, -1);
    (void)a1;

    // Reserve some budget for ordering stage
    int reserveOrder = max(1000, (it.n - 1) * (it.n - 1) + 5); // <= 9806 for n<=100
    int budgetDescent = QMAX - reserveOrder - it.qcnt;
    if (budgetDescent < 0) budgetDescent = 0;

    vector<int> rings(it.n);
    iota(rings.begin(), rings.end(), 0);

    auto shuffle_rings = [&]() {
        shuffle(rings.begin(), rings.end(), rng);
    };

    shuffle_rings();

    // Try to reduce a to 0
    int stagnation = 0;
    while (a > 0 && it.qcnt < QMAX - reserveOrder) {
        bool improved = false;

        // Try to find a strict improvement (-1)
        for (int x : rings) {
            if (it.qcnt >= QMAX - reserveOrder) break;
            for (int d : {+1, -1}) {
                if (it.qcnt >= QMAX - reserveOrder) break;
                int na = it.query(x, d);
                if (na < a) {
                    a = na;
                    improved = true;
                    stagnation = 0;

                    // Greedily continue in same direction while improving
                    while (a > 0 && it.qcnt < QMAX - reserveOrder) {
                        int nb = it.query(x, d);
                        if (nb < a) {
                            a = nb;
                        } else {
                            // revert last move
                            a = it.query(x, -d);
                            break;
                        }
                    }
                    break;
                } else {
                    // revert
                    a = it.query(x, -d);
                }
            }
            if (improved) break;
        }

        if (!improved) {
            stagnation++;

            // Try a neutral move to escape plateaus (keep if doesn't increase)
            bool moved = false;
            shuffle_rings();
            for (int x : rings) {
                if (it.qcnt >= QMAX - reserveOrder) break;
                for (int d : {+1, -1}) {
                    if (it.qcnt >= QMAX - reserveOrder) break;
                    int na = it.query(x, d);
                    if (na <= a) {
                        a = na;
                        moved = true;
                        break;
                    } else {
                        a = it.query(x, -d);
                    }
                }
                if (moved) break;
            }

            if (!moved) {
                // As a last resort, accept a random move (even if it increases)
                if (it.qcnt >= QMAX - reserveOrder) break;
                int x = rings[rng() % rings.size()];
                int d = (rng() & 1) ? +1 : -1;
                a = it.query(x, d);
            }

            if (stagnation >= 50) {
                shuffle_rings();
                stagnation = 0;
            }
        }
    }

    // If we couldn't reach a==0, output something to terminate.
    // (In a real contest, this would likely be judged wrong, but we must end interaction.)
    if (a != 0) {
        vector<int> p(it.n, 0);
        it.answer(p);
        return 0;
    }

    // Determine cyclic order of rings in the partition (a==0).
    // Start the chain: rotate ring 0 clockwise by 1 => a becomes 1.
    if (it.qcnt >= QMAX) return 0;
    int curA = it.query(0, +1);

    vector<int> order;
    order.reserve(it.n);
    vector<char> used(it.n, 0);
    order.push_back(0);
    used[0] = 1;

    for (int step = 1; step < it.n; step++) {
        int expected = (step == it.n - 1 ? 0 : 1);
        int found = -1;

        for (int cand = 0; cand < it.n; cand++) {
            if (used[cand]) continue;
            if (it.qcnt >= QMAX) break;
            int na = it.query(cand, +1);
            if (na == expected) {
                found = cand;
                curA = na;
                break;
            } else {
                // revert
                curA = it.query(cand, -1);
            }
        }

        if (found == -1) {
            // Fallback: stop with zeros
            vector<int> p(it.n, 0);
            it.answer(p);
            return 0;
        }

        used[found] = 1;
        order.push_back(found);
    }

    // Compute p based on order: p[ring] = position * m mod N
    vector<int> pos(it.n, 0);
    for (int i = 0; i < it.n; i++) pos[order[i]] = i;

    vector<int> p(it.n, 0);
    for (int i = 1; i < it.n; i++) {
        long long val = 1LL * pos[i] * it.m;
        p[i] = (int)(val % it.N);
    }

    it.answer(p);
    return 0;
}