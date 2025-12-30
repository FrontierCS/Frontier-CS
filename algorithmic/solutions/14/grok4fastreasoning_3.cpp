#include <bits/stdc++.h>
using namespace std;

int main() {
    unordered_map<int, long long> pos_map;
    long long current_total = 0;
    long long M = 40000;
    cout << "walk 0" << endl;
    int s;
    cin >> s;
    pos_map[s] = 0;

    // Baby steps
    for (long long step = 1; step <= M; ++step) {
        cout << "walk 1" << endl;
        int l;
        cin >> l;
        current_total = step;
        if (pos_map.count(l)) {
            long long nn = current_total - pos_map[l];
            cout << "guess " << nn << endl;
            return 0;
        }
        pos_map[l] = current_total;
    }

    // Giant steps
    for (long long gstep = 1; gstep <= 50000; ++gstep) {
        cout << "walk " << M << endl;
        int l;
        cin >> l;
        current_total += M;
        if (pos_map.count(l)) {
            long long nn = current_total - pos_map[l];
            cout << "guess " << nn << endl;
            return 0;
        }
    }

    // Should not reach here
    return 0;
}