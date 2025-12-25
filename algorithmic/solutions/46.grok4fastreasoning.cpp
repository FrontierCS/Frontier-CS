#include <bits/stdc++.h>
using namespace std;

long long compute_makespan(const vector<vector<int>>& ord, const vector<vector<int>>& stage, const vector<vector<int>>& proc, int J, int M) {
    vector<vector<long long>> startt(J, vector<long long>(M, 0LL));
    int maxiter = J * M + 1;
    int iter = 0;
    bool changed;
    do {
        changed = false;
        // job precedences
        for (int j = 0; j < J; j++) {
            for (int k = 1; k < M; k++) {
                long long cand = startt[j][k - 1] + (long long)proc[j][k - 1];
                if (cand > startt[j][k]) {
                    startt[j][k] = cand;
                    changed = true;
                }
            }
        }
        // machine constraints
        for (int m = 0; m < M; m++) {
            for (int pos = 1; pos < J; pos++) {
                int j1 = ord[m][pos - 1];
                int k1 = stage[j1][m];
                int j2 = ord[m][pos];
                int k2 = stage[j2][m];
                long long cand = startt[j1][k1] + (long long)proc[j1][k1];
                if (cand > startt[j2][k2]) {
                    startt[j2][k2] = cand;
                    changed = true;
                }
            }
        }
        iter++;
    } while (changed && iter < maxiter);
    if (changed) {
        return LLONG_MAX / 2;
    }
    long long ms = 0;
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            long long fin = startt[j][k] + (long long)proc[j][k];
            ms = max(ms, fin);
        }
    }
    return ms;
}

int main() {
    int J, M;
    cin >> J >> M;
    vector<vector<int>> machine_seq(J, vector<int>(M));
    vector<vector<int>> proc(J, vector<int>(M));
    vector<vector<int>> stage(J, vector<int>(M, -1));
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            cin >> machine_seq[j][k] >> proc[j][k];
            stage[j][machine_seq[j][k]] = k;
        }
    }
    // Simulation to get initial order
    vector<long long> machine_avail(M, 0);
    vector<int> job_pos(J, 0);
    vector<long long> job_avail(J, 0);
    vector<vector<int>> order(M);
    for (int step = 0; step < J * M; step++) {
        int best_j = -1;
        long long best_time = LLONG_MAX;
        int best_p = INT_MAX;
        for (int jj = 0; jj < J; jj++) {
            if (job_pos[jj] >= M) continue;
            int kk = job_pos[jj];
            int mm = machine_seq[jj][kk];
            long long ps = max(job_avail[jj], machine_avail[mm]);
            int pp = proc[jj][kk];
            bool better = (ps < best_time) ||
                          (ps == best_time && (pp < best_p ||
                          (pp == best_p && jj < best_j)));
            if (better) {
                best_time = ps;
                best_p = pp;
                best_j = jj;
            }
        }
        assert(best_j != -1);
        int kk = job_pos[best_j];
        int mm = machine_seq[best_j][kk];
        long long st = best_time;
        long long ft = st + proc[best_j][kk];
        order[mm].push_back(best_j);
        machine_avail[mm] = ft;
        job_avail[best_j] = ft;
        job_pos[best_j]++;
    }
    // Local search
    srand(time(NULL));
    long long current_ms = compute_makespan(order, stage, proc, J, M);
    const int NUM_TRIALS = 10000;
    for (int trial = 0; trial < NUM_TRIALS; trial++) {
        int m = rand() % M;
        int i = rand() % (J - 1);
        swap(order[m][i], order[m][i + 1]);
        long long new_ms = compute_makespan(order, stage, proc, J, M);
        if (new_ms < current_ms && new_ms != LLONG_MAX / 2) {
            current_ms = new_ms;
        } else {
            swap(order[m][i], order[m][i + 1]);
        }
    }
    // Output
    for (int m = 0; m < M; m++) {
        for (int i = 0; i < J; i++) {
            if (i > 0) cout << " ";
            cout << order[m][i];
        }
        cout << endl;
    }
    return 0;
}