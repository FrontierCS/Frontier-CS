#include <iostream>
#include <vector>
#include <numeric>
#include <map>

using namespace std;

long long N;

int query(int x, int d) {
    cout << "? " << x << " " << d << endl;
    int result;
    cin >> result;
    return result;
}

int get_unblocked() {
    // A non-destructive way to get current unblocked count
    // by moving a ring and then moving it back.
    int res = query(0, 1);
    query(0, -1);
    return res;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    N = (long long)n * m;

    vector<long long> p(n, -1);
    vector<long long> current_pos(n, 0);
    
    vector<int> group_id(n);
    int groups = 0;
    map<vector<int>, int> sig_to_group;
    
    int initial_unblocked = get_unblocked();

    for (int i = 0; i < n; ++i) {
        vector<int> signature;
        int last_unblocked = initial_unblocked;
        for (int k = 0; k < m; ++k) {
            int current_unblocked = query(i, 1);
            signature.push_back(current_unblocked - last_unblocked);
            last_unblocked = current_unblocked;
        }
        for (int k = 0; k < m; ++k) {
            query(i, -1);
        }

        if (sig_to_group.find(signature) == sig_to_group.end()) {
            sig_to_group[signature] = groups++;
        }
        group_id[i] = sig_to_group[signature];
    }
    
    vector<int> rep_of_group(groups, -1);
    vector<int> group_reps;
    for(int i = 0; i < n; ++i) {
        if (rep_of_group[group_id[i]] == -1) {
            rep_of_group[group_id[i]] = i;
            group_reps.push_back(i);
        }
    }

    p[group_reps[0]] = 0;

    int ref_ring = group_reps[0];

    for (size_t rep_idx = 1; rep_idx < group_reps.size(); ++rep_idx) {
        int ring_to_find = group_reps[rep_idx];
        
        int unblocked_before_move = get_unblocked();
        int d_ref_base = query(ref_ring, 1) - unblocked_before_move;
        query(ref_ring, -1);

        for (long long d = 0; d < N; ++d) {
            int unblocked_after_move = query(ring_to_find, 1);
            current_pos[ring_to_find] = (current_pos[ring_to_find] + 1) % N;
            
            int d_ref_curr = query(ref_ring, 1) - unblocked_after_move;
            query(ref_ring, -1);
            
            if (d_ref_curr == d_ref_base) {
                p[ring_to_find] = (N - current_pos[ring_to_find]) % N;
                break;
            }
        }
    }
    
    for (int i = 0; i < n; ++i) {
      if(p[i] == -1) {
        int rep = rep_of_group[group_id[i]];
        p[i] = p[rep];
      }
    }

    cout << "! ";
    for (int i = 1; i < n; ++i) {
        long long final_pi = (p[i] + current_pos[i] - current_pos[0] + N) % N;
        cout << final_pi << (i == n - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}