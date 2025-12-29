#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <set>

using namespace std;

int n, m;
long long N;

int query(int r, int d) {
    cout << "? " << r << " " << d << endl;
    int res;
    cin >> res;
    return res;
}

vector<int> get_counts() {
    vector<int> counts;
    counts.reserve(N);
    for (int i = 0; i < N; ++i) {
        counts.push_back(query(0, 1));
    }
    return counts;
}

vector<int> find_peaks(const vector<int>& a) {
    vector<int> peaks;
    for (int i = 0; i < N; ++i) {
        int prev = a[(i - 1 + N) % N];
        int next = a[(i + 1) % N];
        if (a[i] > prev && a[i] > next) {
            peaks.push_back(i);
        }
    }
    return peaks;
}

vector<long long> p_initial;
vector<long long> final_pos;

void solve(vector<int> rings, const vector<int>& p_indices) {
    if (rings.empty()) {
        return;
    }

    if (rings.size() == 1) {
        if (!p_indices.empty()) {
            p_initial[rings[0] - 1] = p_indices[0];
        }
        return;
    }

    int mid = rings.size() / 2;
    vector<int> left_rings(rings.begin(), rings.begin() + mid);
    vector<int> right_rings(rings.begin() + mid, rings.end());

    for (int r : left_rings) {
        query(r, 1);
        final_pos[r]++;
    }

    vector<int> A_prime = get_counts();
    final_pos[0] += N;

    for (int r : left_rings) {
        query(r, -1);
        final_pos[r]--;
    }

    vector<int> p_prime_indices = find_peaks(A_prime);
    
    set<int> p_indices_set(p_indices.begin(), p_indices.end());
    set<int> p_prime_indices_set(p_prime_indices.begin(), p_prime_indices.end());
    
    vector<int> left_p, right_p;
    for (int p_idx : p_indices) {
        bool moved = p_prime_indices_set.count((p_idx - 1 + N) % N);
        bool unmoved = p_prime_indices_set.count(p_idx);

        if (moved) {
            left_p.push_back(p_idx);
        }
        if (!moved || (moved && unmoved)) {
            // If peak remains, could be due to right_rings
            // or a mix. Assign to right for further division.
            right_p.push_back(p_idx);
        }
    }
    
    solve(left_rings, left_p);
    solve(right_rings, right_p);
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    N = n * m;

    p_initial.resize(n - 1);
    final_pos.resize(n, 0);
    
    vector<int> A = get_counts();
    final_pos[0] += N;

    vector<int> p_indices = find_peaks(A);

    vector<int> all_rings;
    if (n > 1) {
        all_rings.resize(n - 1);
        iota(all_rings.begin(), all_rings.end(), 1);
    }

    solve(all_rings, p_indices);

    cout << "! ";
    for (int i = 0; i < n - 1; ++i) {
        long long pi = (p_initial[i] + final_pos[i + 1] - final_pos[0]);
        pi %= N;
        if (pi < 0) pi += N;
        cout << pi << (i == n - 2 ? "" : " ");
    }
    cout << endl;

    return 0;
}