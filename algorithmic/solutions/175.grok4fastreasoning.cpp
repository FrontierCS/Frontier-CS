#include <bits/stdc++.h>
using namespace std;

bool is_true(int l, const vector<int>& assign) {
    int v = abs(l);
    return l > 0 ? assign[v] : 1 - assign[v];
}

void compute_deltas(vector<int>& delta, const vector<vector<int>>& clauses, int m, const vector<int>& assign, int n) {
    delta.assign(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int l1 = clauses[i][0], l2 = clauses[i][1], l3 = clauses[i][2];
        int v1 = abs(l1), v2 = abs(l2), v3 = abs(l3);
        bool t1 = l1 > 0 ? assign[v1] : 1 - assign[v1];
        bool t2 = l2 > 0 ? assign[v2] : 1 - assign[v2];
        bool t3 = l3 > 0 ? assign[v3] : 1 - assign[v3];
        if (!t2 && !t3) {
            if (t1) delta[v1] -= 1;
            else delta[v1] += 1;
        }
        if (!t1 && !t3) {
            if (t2) delta[v2] -= 1;
            else delta[v2] += 1;
        }
        if (!t1 && !t2) {
            if (t3) delta[v3] -= 1;
            else delta[v3] += 1;
        }
    }
}

void flip_var(int v, vector<int>& assign, vector<int>& delta, const vector<vector<int>>& clauses, const vector<vector<int>>& var_clauses) {
    const auto& cls_list = var_clauses[v];
    // Subtract old contributions
    for (int cid : cls_list) {
        int l1 = clauses[cid][0], l2 = clauses[cid][1], l3 = clauses[cid][2];
        int v1 = abs(l1), v2 = abs(l2), v3 = abs(l3);
        bool t1 = l1 > 0 ? assign[v1] : 1 - assign[v1];
        bool t2 = l2 > 0 ? assign[v2] : 1 - assign[v2];
        bool t3 = l3 > 0 ? assign[v3] : 1 - assign[v3];
        // Undo
        if (!t2 && !t3) {
            if (t1) delta[v1] += 1;
            else delta[v1] -= 1;
        }
        if (!t1 && !t3) {
            if (t2) delta[v2] += 1;
            else delta[v2] -= 1;
        }
        if (!t1 && !t2) {
            if (t3) delta[v3] += 1;
            else delta[v3] -= 1;
        }
    }
    // Flip
    assign[v] = 1 - assign[v];
    // Add new contributions
    for (int cid : cls_list) {
        int l1 = clauses[cid][0], l2 = clauses[cid][1], l3 = clauses[cid][2];
        int v1 = abs(l1), v2 = abs(l2), v3 = abs(l3);
        bool t1 = l1 > 0 ? assign[v1] : 1 - assign[v1];
        bool t2 = l2 > 0 ? assign[v2] : 1 - assign[v2];
        bool t3 = l3 > 0 ? assign[v3] : 1 - assign[v3];
        // Add
        if (!t2 && !t3) {
            if (t1) delta[v1] -= 1;
            else delta[v1] += 1;
        }
        if (!t1 && !t3) {
            if (t2) delta[v2] -= 1;
            else delta[v2] += 1;
        }
        if (!t1 && !t2) {
            if (t3) delta[v3] -= 1;
            else delta[v3] += 1;
        }
    }
}

int get_score(const vector<int>& assign, const vector<vector<int>>& clauses, int m) {
    int s = 0;
    for (int i = 0; i < m; i++) {
        if (is_true(clauses[i][0], assign) ||
            is_true(clauses[i][1], assign) ||
            is_true(clauses[i][2], assign)) {
            s++;
        }
    }
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));
    int n, m;
    cin >> n >> m;
    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            cout << 0 << (i < n ? " " : "\n");
        }
        return 0;
    }
    vector<vector<int>> clauses(m, vector<int>(3));
    for (int i = 0; i < m; i++) {
        cin >> clauses[i][0] >> clauses[i][1] >> clauses[i][2];
    }
    vector<vector<int>> var_clauses(n + 1);
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < 3; j++) {
            int v = abs(clauses[i][j]);
            var_clauses[v].push_back(i);
        }
    }
    int best_score = -1;
    vector<int> best_assign(n + 1);
    const int NUM_RESTARTS = 30;
    const int MAX_FLIPS = 20000;
    for (int r = 0; r < NUM_RESTARTS; r++) {
        vector<int> assign(n + 1);
        for (int i = 1; i <= n; i++) {
            assign[i] = rand() % 2;
        }
        vector<int> delta(n + 1);
        compute_deltas(delta, clauses, m, assign, n);
        int flips = 0;
        while (flips < MAX_FLIPS) {
            int best_d = INT_MIN;
            int best_v = -1;
            for (int i = 1; i <= n; i++) {
                if (delta[i] > best_d) {
                    best_d = delta[i];
                    best_v = i;
                }
            }
            if (best_d <= 0) break;
            flip_var(best_v, assign, delta, clauses, var_clauses);
            flips++;
        }
        int curr_score = get_score(assign, clauses, m);
        if (curr_score > best_score) {
            best_score = curr_score;
            best_assign = assign;
        }
    }
    for (int i = 1; i <= n; i++) {
        cout << best_assign[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}