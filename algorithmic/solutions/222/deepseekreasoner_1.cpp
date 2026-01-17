#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_map>
#include <cmath>

using namespace std;

const int M = 1000; // baby step count, sqrt(1e6) ~ 1000
const int V = 1;    // fixed starting vertex

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    for (int g = 0; g < n; ++g) {
        unordered_map<long long, int> mp; // vertex -> index i
        long long first_vertex = -1;
        long long d_multiple = -1;

        // Baby steps: i = 0 .. M-1
        for (int i = 0; i < M; ++i) {
            long long x = 1 + i;
            cout << "? " << V << " " << x << endl;
            long long a;
            cin >> a;
            if (i == 0) first_vertex = a;
            if (mp.find(a) != mp.end()) {
                // collision within baby steps
                int i0 = mp[a];
                d_multiple = i - i0;
                break;
            } else {
                mp[a] = i;
            }
        }

        // Giant steps if no collision yet
        if (d_multiple == -1) {
            for (int j = 1; j <= M; ++j) {
                long long x = 1 + (long long)j * M;
                cout << "? " << V << " " << x << endl;
                long long b;
                cin >> b;
                if (mp.find(b) != mp.end()) {
                    int i0 = mp[b];
                    d_multiple = (long long)j * M - i0;
                    break;
                }
            }
        }

        // Now d_multiple is a positive multiple of the cycle length s.
        // Find all divisors of d_multiple.
        vector<long long> divisors;
        for (long long t = 1; t * t <= d_multiple; ++t) {
            if (d_multiple % t == 0) {
                divisors.push_back(t);
                if (t != d_multiple / t) {
                    divisors.push_back(d_multiple / t);
                }
            }
        }
        sort(divisors.begin(), divisors.end());

        long long s_candidate = -1;
        for (long long t : divisors) {
            if (t >= 3 && t <= 1000000) {
                long long x_test = 1 + t;
                cout << "? " << V << " " << x_test << endl;
                long long c_test;
                cin >> c_test;
                if (c_test == first_vertex) {
                    s_candidate = t;
                    break;
                }
            }
        }

        // Output the answer
        cout << "! " << s_candidate << endl;
        int resp;
        cin >> resp;
        if (resp == -1) {
            return 0; // Wrong answer
        }
    }
    return 0;
}