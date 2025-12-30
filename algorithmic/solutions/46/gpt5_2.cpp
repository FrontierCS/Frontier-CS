#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Candidate {
    int job;
    int k; // position in job
    int m;
    ll p;
    ll est;
    ll eft;
    ll remWorkJob;
    ll remLoadMach;
    uint32_t noise;
};

enum Rule {
    EST_SPT = 0,
    EST_LPT = 1,
    EST_MWR = 2,
    EST_LWR = 3,
    EST_BOTTLENECK = 4,
    EST_EFT = 5
};

struct ScheduleResult {
    vector<vector<int>> machineOrder; // M x J
    ll makespan = (ll)4e18;
};

static inline bool better_by_rule(const Candidate& a, const Candidate& b, Rule rule) {
    // Assumes a.est == b.est already checked by caller for primary key.
    switch (rule) {
        case EST_SPT: {
            if (a.p != b.p) return a.p < b.p;
            if (a.eft != b.eft) return a.eft < b.eft;
            if (a.remWorkJob != b.remWorkJob) return a.remWorkJob < b.remWorkJob;
            if (a.remLoadMach != b.remLoadMach) return a.remLoadMach < b.remLoadMach;
            if (a.job != b.job) return a.job < b.job;
            return a.noise < b.noise;
        }
        case EST_LPT: {
            if (a.p != b.p) return a.p > b.p;
            if (a.eft != b.eft) return a.eft < b.eft;
            if (a.remWorkJob != b.remWorkJob) return a.remWorkJob > b.remWorkJob;
            if (a.remLoadMach != b.remLoadMach) return a.remLoadMach > b.remLoadMach;
            if (a.job != b.job) return a.job < b.job;
            return a.noise < b.noise;
        }
        case EST_MWR: {
            if (a.remWorkJob != b.remWorkJob) return a.remWorkJob > b.remWorkJob;
            if (a.p != b.p) return a.p < b.p;
            if (a.remLoadMach != b.remLoadMach) return a.remLoadMach > b.remLoadMach;
            if (a.eft != b.eft) return a.eft < b.eft;
            if (a.job != b.job) return a.job < b.job;
            return a.noise < b.noise;
        }
        case EST_LWR: {
            if (a.remWorkJob != b.remWorkJob) return a.remWorkJob < b.remWorkJob;
            if (a.p != b.p) return a.p < b.p;
            if (a.remLoadMach != b.remLoadMach) return a.remLoadMach < b.remLoadMach;
            if (a.eft != b.eft) return a.eft < b.eft;
            if (a.job != b.job) return a.job < b.job;
            return a.noise < b.noise;
        }
        case EST_BOTTLENECK: {
            if (a.remLoadMach != b.remLoadMach) return a.remLoadMach > b.remLoadMach;
            if (a.eft != b.eft) return a.eft < b.eft;
            if (a.p != b.p) return a.p < b.p;
            if (a.remWorkJob != b.remWorkJob) return a.remWorkJob > b.remWorkJob;
            if (a.job != b.job) return a.job < b.job;
            return a.noise < b.noise;
        }
        case EST_EFT:
        default: {
            if (a.eft != b.eft) return a.eft < b.eft;
            if (a.p != b.p) return a.p < b.p;
            if (a.remWorkJob != b.remWorkJob) return a.remWorkJob < b.remWorkJob;
            if (a.remLoadMach != b.remLoadMach) return a.remLoadMach > b.remLoadMach;
            if (a.job != b.job) return a.job < b.job;
            return a.noise < b.noise;
        }
    }
}

static ScheduleResult serialSGS(
    const vector<vector<int>>& jobM,
    const vector<vector<ll>>& jobP,
    const vector<ll>& jobTotal,
    const vector<ll>& machTotal,
    Rule rule,
    int rclSize,
    uint32_t seed)
{
    int J = (int)jobM.size();
    int M = (int)jobM[0].size();
    int Nops = J * M;

    vector<int> jobNext(J, 0);
    vector<ll> jobReady(J, 0);
    vector<ll> machFree(M, 0);
    vector<ll> remWorkJob = jobTotal;
    vector<ll> remLoadMach = machTotal;

    vector<vector<int>> seq(M);
    seq.assign(M, vector<int>()); seq.shrink_to_fit();
    for (int m = 0; m < M; ++m) seq[m].reserve(J);

    std::mt19937 rng(seed);

    int scheduled = 0;
    while (scheduled < Nops) {
        ll bestEst = LLONG_MAX;
        // Build candidate list with minimal est
        vector<Candidate> cand;
        cand.reserve(J);
        for (int j = 0; j < J; ++j) {
            int k = jobNext[j];
            if (k >= M) continue;
            int m = jobM[j][k];
            ll p = jobP[j][k];
            ll est = jobReady[j] > machFree[m] ? jobReady[j] : machFree[m];
            if (est < bestEst) {
                bestEst = est;
                cand.clear();
            }
            if (est == bestEst) {
                Candidate c;
                c.job = j; c.k = k; c.m = m; c.p = p;
                c.est = est;
                c.eft = est + p;
                c.remWorkJob = remWorkJob[j];
                c.remLoadMach = remLoadMach[m];
                c.noise = rng();
                cand.push_back(c);
            }
        }

        // If somehow no candidate (shouldn't happen), break
        if (cand.empty()) {
            // Fallback: pick any available operation (should not happen, but be safe)
            for (int j = 0; j < J; ++j) {
                int k = jobNext[j];
                if (k >= M) continue;
                int m = jobM[j][k];
                ll p = jobP[j][k];
                Candidate c;
                ll est = max(jobReady[j], machFree[m]);
                c.job = j; c.k = k; c.m = m; c.p = p;
                c.est = est; c.eft = est + p;
                c.remWorkJob = remWorkJob[j];
                c.remLoadMach = remLoadMach[m];
                c.noise = rng();
                cand.push_back(c);
            }
        }

        // Sort the earliest candidates by rule
        sort(cand.begin(), cand.end(), [&](const Candidate& a, const Candidate& b){
            if (a.est != b.est) return a.est < b.est; // should be equal here, but keep stable
            return better_by_rule(a, b, rule);
        });

        int pickIndex = 0;
        if (rclSize > 1) {
            int sz = (int)cand.size();
            int top = min(rclSize, sz);
            pickIndex = uniform_int_distribution<int>(0, top - 1)(rng);
        }
        const Candidate &ch = cand[pickIndex];

        // Schedule chosen candidate
        ll start = ch.est;
        ll finish = start + ch.p;

        seq[ch.m].push_back(ch.job);

        jobNext[ch.job] = ch.k + 1;
        jobReady[ch.job] = finish;
        machFree[ch.m] = finish;

        remWorkJob[ch.job] -= ch.p;
        remLoadMach[ch.m] -= ch.p;

        scheduled++;
    }

    ll makespan = 0;
    for (int j = 0; j < J; ++j) makespan = max(makespan, jobReady[j]);

    ScheduleResult res;
    res.machineOrder = move(seq);
    res.makespan = makespan;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int J, M;
    if (!(cin >> J >> M)) {
        return 0;
    }
    vector<vector<int>> jobM(J, vector<int>(M));
    vector<vector<long long>> jobP(J, vector<long long>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m; long long p;
            cin >> m >> p;
            jobM[j][k] = m;
            jobP[j][k] = p;
        }
    }

    // Precompute totals
    vector<ll> jobTotal(J, 0), machTotal(M, 0);
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            ll p = jobP[j][k];
            jobTotal[j] += p;
        }
    }
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m = jobM[j][k];
            machTotal[m] += jobP[j][k];
        }
    }

    // Time-bounded multi-start with different rules and RCL sizes
    using clock_type = chrono::steady_clock;
    auto t0 = clock_type::now();
    // Aim for around ~0.9s time budget
    const double TIME_BUDGET_SEC = 0.9;

    vector<Rule> rules = {
        EST_EFT, EST_SPT, EST_MWR, EST_BOTTLENECK, EST_LPT, EST_LWR
    };
    vector<int> rclOptions = {1, 2, 3};

    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ 0x9e3779b97f4a7c15ULL);
    ScheduleResult best;
    best.makespan = (ll)4e18;

    int iter = 0;
    // Ensure at least some deterministic runs
    for (Rule rule : rules) {
        for (int rcl : rclOptions) {
            uint32_t seed = rng();
            ScheduleResult cur = serialSGS(jobM, jobP, jobTotal, machTotal, rule, rcl, seed);
            if (cur.makespan < best.makespan) best = move(cur);
            iter++;
            auto t1 = clock_type::now();
            double elapsed = chrono::duration<double>(t1 - t0).count();
            if (elapsed > TIME_BUDGET_SEC) break;
        }
        auto t1 = clock_type::now();
        double elapsed = chrono::duration<double>(t1 - t0).count();
        if (elapsed > TIME_BUDGET_SEC) break;
    }

    // Additional random restarts until time runs out
    while (true) {
        auto t1 = clock_type::now();
        double elapsed = chrono::duration<double>(t1 - t0).count();
        if (elapsed > TIME_BUDGET_SEC) break;

        Rule rule = rules[uniform_int_distribution<int>(0, (int)rules.size() - 1)(rng)];
        int rcl = rclOptions[uniform_int_distribution<int>(0, (int)rclOptions.size() - 1)(rng)];
        uint32_t seed = rng();
        ScheduleResult cur = serialSGS(jobM, jobP, jobTotal, machTotal, rule, rcl, seed);
        if (cur.makespan < best.makespan) best = move(cur);
        iter++;
    }

    // Output the best machine orders
    // Exactly M lines, each a permutation of 0..J-1
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < (int)best.machineOrder[m].size(); ++i) {
            if (i) cout << ' ';
            cout << best.machineOrder[m][i];
        }
        // If for any reason sequence size is less than J (shouldn't happen), fill missing jobs arbitrarily without duplicates
        if ((int)best.machineOrder[m].size() < J) {
            vector<int> used(J, 0);
            for (int x : best.machineOrder[m]) if (0 <= x && x < J) used[x] = 1;
            for (int j = 0; j < J; ++j) if (!used[j]) {
                if (!best.machineOrder[m].empty() || (int)best.machineOrder[m].size() > 0) cout << ' ';
                cout << j;
            }
        }
        cout << '\n';
    }

    return 0;
}