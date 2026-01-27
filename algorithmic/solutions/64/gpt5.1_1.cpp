#include <bits/stdc++.h>
using namespace std;

int n;
long long T;
vector<long long> a;
long long global_best_err;
long long bestSum;
string bestMask;

inline long long myabs(long long x) {
    return x >= 0 ? x : -x;
}

void update_best(const vector<int> &x, long long sum) {
    long long err = myabs(sum - T);
    if (err < global_best_err) {
        global_best_err = err;
        bestSum = sum;
        if ((int)bestMask.size() != n) bestMask.assign(n, '0');
        for (int i = 0; i < n; ++i) bestMask[i] = x[i] ? '1' : '0';
    }
}

void local_search(vector<int> &x, long long &sum) {
    const int MAX_FLIPS = 200;
    for (int step = 0; step < MAX_FLIPS; ++step) {
        long long currErr = myabs(sum - T);
        int bestI = -1;
        long long bestErr = currErr;
        long long bestNewSum = sum;
        for (int i = 0; i < n; ++i) {
            long long newSum = x[i] ? sum - a[i] : sum + a[i];
            long long newErr = myabs(newSum - T);
            if (newErr < bestErr) {
                bestErr = newErr;
                bestNewSum = newSum;
                bestI = i;
            }
        }
        if (bestI == -1) break;
        x[bestI] ^= 1;
        sum = bestNewSum;
        update_best(x, sum);
        if (global_best_err == 0) return;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> T)) return 0;
    a.resize(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    bestMask.assign(n, '0');
    global_best_err = myabs(0 - T);
    bestSum = 0;

    vector<int> x(n, 0);
    long long sum = 0;
    update_best(x, sum);

    long long sumAll = 0;
    for (int i = 0; i < n; ++i) sumAll += a[i];

    // All ones start
    x.assign(n, 1);
    sum = sumAll;
    update_best(x, sum);
    local_search(x, sum);
    if (global_best_err == 0) {
        cout << bestMask << '\n';
        return 0;
    }

    // Greedy descending
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j) {
        return a[i] > a[j];
    });
    x.assign(n, 0);
    sum = 0;
    for (int idx : order) {
        long long newSum = sum + a[idx];
        if (myabs(newSum - T) <= myabs(sum - T)) {
            x[idx] = 1;
            sum = newSum;
        }
    }
    update_best(x, sum);
    local_search(x, sum);
    if (global_best_err == 0) {
        cout << bestMask << '\n';
        return 0;
    }

    // Greedy ascending
    sort(order.begin(), order.end(), [&](int i, int j) {
        return a[i] < a[j];
    });
    x.assign(n, 0);
    sum = 0;
    for (int idx : order) {
        long long newSum = sum + a[idx];
        if (myabs(newSum - T) <= myabs(sum - T)) {
            x[idx] = 1;
            sum = newSum;
        }
    }
    update_best(x, sum);
    local_search(x, sum);
    if (global_best_err == 0) {
        cout << bestMask << '\n';
        return 0;
    }

    // All zeros start
    x.assign(n, 0);
    sum = 0;
    update_best(x, sum);
    local_search(x, sum);
    if (global_best_err == 0) {
        cout << bestMask << '\n';
        return 0;
    }

    // Random restarts
    mt19937_64 rng(123456789);
    const int RANDOM_STARTS = 400;
    uniform_int_distribution<int> bitdist(0, 1);

    for (int rs = 0; rs < RANDOM_STARTS; ++rs) {
        if (global_best_err == 0) break;
        x.assign(n, 0);
        sum = 0;
        for (int i = 0; i < n; ++i) {
            x[i] = bitdist(rng);
            if (x[i]) sum += a[i];
        }
        update_best(x, sum);
        local_search(x, sum);
        if (global_best_err == 0) break;
    }

    cout << bestMask << '\n';
    return 0;
}