#include <bits/stdc++.h>
using namespace std;

struct State {
    vector<short> diff;
    int prev_state_id;
    int op_i, op_j;
    State(const vector<short>& d, int pid = -1, int i = -1, int j = -1)
        : diff(d), prev_state_id(pid), op_i(i), op_j(j) {}
};

struct Hash {
    size_t operator()(const vector<short>& v) const {
        size_t h = 0;
        for (short x : v) {
            h = h * 31 + x;
        }
        return h;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int N;
    cin >> N;
    vector<int> A(N), B(N);
    for (int i = 0; i < N; i++) cin >> A[i];
    for (int i = 0; i < N; i++) cin >> B[i];
    
    long long sumA = accumulate(A.begin(), A.end(), 0LL);
    long long sumB = accumulate(B.begin(), B.end(), 0LL);
    if (sumA != sumB) {
        cout << "No\n";
        return 0;
    }
    
    vector<short> init_diff(N);
    for (int i = 0; i < N; i++) {
        init_diff[i] = A[i] - B[i];
    }
    
    // Precompute c_{ij} = B_i - B_j + 1
    vector<vector<short>> c(N, vector<short>(N));
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            c[i][j] = B[i] - B[j] + 1;
        }
    }
    
    const int L = 200; // bound on |diff_i|
    auto in_bound = [&](const vector<short>& d) {
        for (short x : d) {
            if (x < -L || x > L) return false;
        }
        return true;
    };
    
    unordered_map<vector<short>, int, Hash> state_to_id;
    vector<State> states;
    
    queue<int> q;
    int start_id = states.size();
    states.emplace_back(init_diff, -1, -1, -1);
    state_to_id[init_diff] = start_id;
    q.push(start_id);
    
    int target_id = -1;
    
    while (!q.empty()) {
        int id = q.front(); q.pop();
        State& s = states[id];
        
        bool zero = true;
        for (short x : s.diff) {
            if (x != 0) { zero = false; break; }
        }
        if (zero) {
            target_id = id;
            break;
        }
        
        for (int i = 0; i < N; i++) {
            for (int j = i+1; j < N; j++) {
                vector<short> ndiff = s.diff;
                short ci = c[i][j];
                short new_i = ndiff[j] - ci;
                short new_j = ndiff[i] + ci;
                ndiff[i] = new_i;
                ndiff[j] = new_j;
                
                if (!in_bound(ndiff)) continue;
                
                if (state_to_id.find(ndiff) == state_to_id.end()) {
                    int new_id = states.size();
                    states.emplace_back(ndiff, id, i, j);
                    state_to_id[ndiff] = new_id;
                    q.push(new_id);
                }
            }
        }
        
        if (states.size() > 1000000) {
            break;
        }
    }
    
    if (target_id == -1) {
        cout << "No\n";
        return 0;
    }
    
    vector<pair<int,int>> ops;
    int cur = target_id;
    while (cur != start_id) {
        State& s = states[cur];
        ops.emplace_back(s.op_i, s.op_j);
        cur = s.prev_state_id;
    }
    reverse(ops.begin(), ops.end());
    
    cout << "Yes\n";
    cout << ops.size() << "\n";
    for (auto& p : ops) {
        cout << p.first+1 << " " << p.second+1 << "\n";
    }
    
    return 0;
}