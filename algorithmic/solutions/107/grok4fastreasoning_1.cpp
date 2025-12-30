#include <bits/stdc++.h>
using namespace std;

const int MAXP = 3000;
vector<int> primes;
bool is_composite[MAXP + 1];

void sieve() {
    memset(is_composite, 0, sizeof(is_composite));
    is_composite[0] = is_composite[1] = true;
    for (long long i = 2; i <= MAXP; i++) {
        if (!is_composite[i]) {
            primes.push_back(i);
            for (long long j = i * i; j <= MAXP; j += i) {
                is_composite[j] = true;
            }
        }
    }
}

int main() {
    sieve();
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        vector<int> pr = primes;
        sort(pr.rbegin(), pr.rend());
        vector<vector<int>> groups;
        vector<int> current_group;
        unsigned long long current_prod = 1;
        for (int p : pr) {
            unsigned long long pp = p;
            bool can_add = (current_prod <= 1000000000000000000ULL / pp);
            if (can_add) {
                current_group.push_back(p);
                current_prod *= pp;
            } else {
                if (!current_group.empty()) {
                    groups.push_back(current_group);
                }
                current_group = {p};
                current_prod = p;
            }
        }
        if (!current_group.empty()) {
            groups.push_back(current_group);
        }
        set<int> small_set;
        for (auto& group : groups) {
            unsigned long long Q = 1;
            for (int pp : group) {
                Q *= (unsigned long long)pp;
            }
            cout << "0 " << Q << endl;
            cout.flush();
            long long g;
            cin >> g;
            if (g == 1) continue;
            for (int p : group) {
                if (g % p == 0) {
                    small_set.insert(p);
                }
            }
        }
        map<int, int> factors;
        for (int p : small_set) {
            unsigned long long poww = 1;
            unsigned long long pp = p;
            while (true) {
                if (pp != 0 && poww > 1000000000000000000ULL / pp) break;
                poww *= pp;
            }
            cout << "0 " << poww << endl;
            cout.flush();
            long long gg;
            cin >> gg;
            int e = 0;
            long long temp = gg;
            while (temp % p == 0) {
                temp /= p;
                e++;
            }
            if (temp == 1 || gg == 1) {
                factors[p] = e;
            } else {
                factors[p] = 1; // fallback
            }
        }
        long long d_S = 1;
        for (auto& pf : factors) {
            d_S *= (pf.second + 1LL);
        }
        long long ans = 2LL * d_S;
        cout << "1 " << ans << endl;
        cout.flush();
    }
    return 0;
}