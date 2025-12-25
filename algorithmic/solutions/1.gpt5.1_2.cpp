#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
};

const long long MAX_MASS = 20000000LL;
const long long MAX_VOL  = 25000000LL;
const double EPS = 1e-12;

vector<Item> items;
int n;

void skipWhitespace(const string &s, size_t &pos) {
    while (pos < s.size() && isspace((unsigned char)s[pos])) pos++;
}

string parseString(const string &s, size_t &pos) {
    skipWhitespace(s, pos);
    if (pos >= s.size() || s[pos] != '"') return "";
    pos++;
    size_t start = pos;
    while (pos < s.size() && s[pos] != '"') pos++;
    string res = s.substr(start, pos - start);
    if (pos < s.size() && s[pos] == '"') pos++;
    return res;
}

long long parseInt(const string &s, size_t &pos) {
    skipWhitespace(s, pos);
    bool neg = false;
    if (pos < s.size() && s[pos] == '-') {
        neg = true;
        pos++;
    }
    long long val = 0;
    while (pos < s.size() && isdigit((unsigned char)s[pos])) {
        val = val * 10 + (s[pos] - '0');
        pos++;
    }
    return neg ? -val : val;
}

enum Mode { MASS, VOL, SUMD, MASS_HEAVY, VOL_HEAVY, MAXR, VALUE_ONLY };

double computeScore(Mode mode, int idx) {
    const Item &it = items[idx];
    double mRel = (double)it.m / (double)MAX_MASS;
    double lRel = (double)it.l / (double)MAX_VOL;
    switch (mode) {
        case MASS:
            return (double)it.v / (double)it.m;
        case VOL:
            return (double)it.v / (double)it.l;
        case SUMD: {
            double denom = mRel + lRel + EPS;
            return (double)it.v / denom;
        }
        case MASS_HEAVY: {
            double denom = 0.7 * mRel + 0.3 * lRel + EPS;
            return (double)it.v / denom;
        }
        case VOL_HEAVY: {
            double denom = 0.3 * mRel + 0.7 * lRel + EPS;
            return (double)it.v / denom;
        }
        case MAXR: {
            double denom = max(mRel, lRel) + EPS;
            return (double)it.v / denom;
        }
        case VALUE_ONLY:
        default:
            return (double)it.v;
    }
}

vector<int> getOrder(Mode mode) {
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b) {
        double sa = computeScore(mode, a);
        double sb = computeScore(mode, b);
        if (sa != sb) return sa > sb;
        const Item &ia = items[a];
        const Item &ib = items[b];
        double wa = (double)ia.m / MAX_MASS + (double)ia.l / MAX_VOL;
        double wb = (double)ib.m / MAX_MASS + (double)ib.l / MAX_VOL;
        if (wa != wb) return wa < wb;
        return a < b;
    });
    return idx;
}

vector<long long> greedyPack(Mode mode) {
    vector<int> order = getOrder(mode);
    vector<long long> x(n, 0);
    long long massUsed = 0, volUsed = 0;
    for (int id : order) {
        const Item &it = items[id];
        if (it.m > MAX_MASS || it.l > MAX_VOL) continue;
        long long remM = MAX_MASS - massUsed;
        long long remL = MAX_VOL - volUsed;
        if (remM <= 0 || remL <= 0) break;
        long long maxByM = remM / it.m;
        long long maxByL = remL / it.l;
        long long take = min(it.q, min(maxByM, maxByL));
        if (take > 0) {
            x[id] += take;
            massUsed += take * it.m;
            volUsed += take * it.l;
        }
    }
    return x;
}

long long evaluateSolution(const vector<long long> &x) {
    long long massUsed = 0, volUsed = 0, val = 0;
    for (int i = 0; i < n; i++) {
        if (x[i] < 0 || x[i] > items[i].q) return -1;
        massUsed += x[i] * items[i].m;
        if (massUsed > MAX_MASS) return -1;
        volUsed += x[i] * items[i].l;
        if (volUsed > MAX_VOL) return -1;
        val += x[i] * items[i].v;
    }
    return val;
}

void fillRemByMode(vector<long long> &x, Mode mode) {
    vector<int> order = getOrder(mode);
    long long massUsed = 0, volUsed = 0;
    for (int i = 0; i < n; i++) {
        massUsed += x[i] * items[i].m;
        volUsed  += x[i] * items[i].l;
    }
    long long remM = MAX_MASS - massUsed;
    long long remL = MAX_VOL - volUsed;
    if (remM <= 0 || remL <= 0) return;
    for (int id : order) {
        const Item &it = items[id];
        if (x[id] >= it.q) continue;
        if (it.m > remM || it.l > remL) continue;
        long long maxByM = remM / it.m;
        long long maxByL = remL / it.l;
        long long canAdd = min(it.q - x[id], min(maxByM, maxByL));
        if (canAdd > 0) {
            x[id] += canAdd;
            remM -= canAdd * it.m;
            remL -= canAdd * it.l;
            if (remM <= 0 || remL <= 0) break;
        }
    }
}

vector<long long> localSearch(const vector<long long> &start) {
    vector<long long> cur = start;
    fillRemByMode(cur, SUMD);
    const int MAX_ITER = 40;
    const int MAX_REMOVE = 3;
    for (int iter = 0; iter < MAX_ITER; ++iter) {
        long long massUsed = 0, volUsed = 0, curVal = 0;
        for (int i = 0; i < n; i++) {
            massUsed += cur[i] * items[i].m;
            volUsed  += cur[i] * items[i].l;
            curVal   += cur[i] * items[i].v;
        }
        long long remM = MAX_MASS - massUsed;
        long long remL = MAX_VOL  - volUsed;
        long long bestDelta = 0;
        int bestI = -1, bestJ = -1;
        long long bestRemCnt = 0, bestAddCnt = 0;

        for (int i = 0; i < n; i++) {
            if (cur[i] == 0) continue;
            const Item &itI = items[i];
            long long maxRem = min(cur[i], (long long)MAX_REMOVE);
            for (long long remCnt = 1; remCnt <= maxRem; ++remCnt) {
                long long freedM = remCnt * itI.m;
                long long freedL = remCnt * itI.l;
                long long M2 = remM + freedM;
                long long L2 = remL + freedL;
                if (M2 <= 0 || L2 <= 0) continue;
                for (int j = 0; j < n; j++) {
                    if (j == i) continue;
                    const Item &itJ = items[j];
                    if (cur[j] >= itJ.q) continue;
                    if (itJ.m > M2 || itJ.l > L2) continue;
                    long long maxByM = M2 / itJ.m;
                    long long maxByL = L2 / itJ.l;
                    long long addCnt = min(itJ.q - cur[j], min(maxByM, maxByL));
                    if (addCnt <= 0) continue;
                    long long delta = addCnt * itJ.v - remCnt * itI.v;
                    if (delta > bestDelta) {
                        bestDelta = delta;
                        bestI = i; bestJ = j;
                        bestRemCnt = remCnt; bestAddCnt = addCnt;
                    }
                }
            }
        }

        if (bestDelta <= 0) break;
        cur[bestI] -= bestRemCnt;
        cur[bestJ] += bestAddCnt;
        fillRemByMode(cur, SUMD);
    }
    return cur;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    size_t pos = 0;
    skipWhitespace(input, pos);
    if (pos < input.size() && input[pos] == '{') pos++;
    skipWhitespace(input, pos);
    items.clear();

    while (pos < input.size()) {
        skipWhitespace(input, pos);
        if (pos < input.size() && input[pos] == '}') {
            pos++;
            break;
        }
        string key = parseString(input, pos);
        skipWhitespace(input, pos);
        if (pos < input.size() && input[pos] == ':') pos++;
        skipWhitespace(input, pos);
        if (pos < input.size() && input[pos] == '[') pos++;

        vector<long long> nums;
        for (int k = 0; k < 4; k++) {
            long long v = parseInt(input, pos);
            nums.push_back(v);
            skipWhitespace(input, pos);
            if (k < 3 && pos < input.size() && input[pos] == ',') {
                pos++;
                skipWhitespace(input, pos);
            }
        }
        skipWhitespace(input, pos);
        if (pos < input.size() && input[pos] == ']') pos++;

        if (nums.size() == 4) {
            Item it;
            it.name = key;
            it.q = nums[0];
            it.v = nums[1];
            it.m = nums[2];
            it.l = nums[3];
            items.push_back(it);
        }

        skipWhitespace(input, pos);
        if (pos < input.size() && input[pos] == ',') {
            pos++;
            continue;
        } else if (pos < input.size() && input[pos] == '}') {
            pos++;
            break;
        }
    }

    n = (int)items.size();
    if (n == 0) {
        cout << "{\n}\n";
        return 0;
    }

    vector<Mode> modes = { MASS, VOL, SUMD, MASS_HEAVY, VOL_HEAVY, MAXR, VALUE_ONLY };

    vector<long long> bestSol(n, 0);
    long long bestVal = evaluateSolution(bestSol); // initial 0

    for (Mode m : modes) {
        vector<long long> sol = greedyPack(m);
        sol = localSearch(sol);
        long long val = evaluateSolution(sol);
        if (val > bestVal) {
            bestVal = val;
            bestSol = sol;
        }
    }

    if (evaluateSolution(bestSol) < 0) {
        bestSol.assign(n, 0);
    }

    cout << "{\n";
    for (int i = 0; i < n; i++) {
        cout << " \"" << items[i].name << "\": " << bestSol[i];
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";

    return 0;
}