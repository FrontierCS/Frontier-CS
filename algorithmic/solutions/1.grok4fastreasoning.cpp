#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    int q;
    long long v, m, l;
};

string input_str;
int pos = 0;

void skip_ws() {
    while (pos < input_str.size() && (input_str[pos] == ' ' || input_str[pos] == '\n' || input_str[pos] == '\t' || input_str[pos] == '\r')) pos++;
}

long long parse_num() {
    skip_ws();
    long long num = 0;
    while (pos < input_str.size() && isdigit(input_str[pos])) {
        num = num * 10 + (input_str[pos] - '0');
        pos++;
    }
    return num;
}

string parse_name() {
    skip_ws();
    if (pos >= input_str.size() || input_str[pos] != '"') assert(false);
    pos++;
    string s;
    while (pos < input_str.size() && input_str[pos] != '"') {
        s += input_str[pos];
        pos++;
    }
    if (pos >= input_str.size() || input_str[pos] != '"') assert(false);
    pos++;
    return s;
}

long long greedy(const vector<Item>& items, vector<int>& cnts, function<double(const Item&)> pri_func) {
    int n = items.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return pri_func(items[a]) > pri_func(items[b]);
    });
    long long rem_m = 20000000LL;
    long long rem_v = 25000000LL;
    fill(cnts.begin(), cnts.end(), 0);
    long long total = 0;
    for (int idx : order) {
        const auto& it = items[idx];
        if (it.m == 0 || it.l == 0) continue;
        long long mk = rem_m / it.m;
        long long lk = rem_v / it.l;
        long long k = min({(long long)it.q, mk, lk});
        if (k > 0) {
            cnts[idx] = (int)k;
            total += k * it.v;
            rem_m -= k * it.m;
            rem_v -= k * it.l;
        }
    }
    return total;
}

int main() {
    input_str.assign((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    pos = 0;
    skip_ws();
    if (pos >= input_str.size() || input_str[pos] != '{') assert(false);
    pos++;
    vector<Item> items;
    while (true) {
        skip_ws();
        if (pos >= input_str.size() || input_str[pos] == '}') {
            pos++;
            break;
        }
        string name = parse_name();
        skip_ws();
        if (pos >= input_str.size() || input_str[pos] != ':') assert(false);
        pos++;
        skip_ws();
        if (pos >= input_str.size() || input_str[pos] != '[') assert(false);
        pos++;
        int qq = (int)parse_num();
        skip_ws();
        if (pos < input_str.size() && input_str[pos] == ',') pos++;
        long long vv = parse_num();
        skip_ws();
        if (pos < input_str.size() && input_str[pos] == ',') pos++;
        long long mm = parse_num();
        skip_ws();
        if (pos < input_str.size() && input_str[pos] == ',') pos++;
        long long ll = parse_num();
        skip_ws();
        if (pos < input_str.size() && input_str[pos] == ']') pos++;
        items.push_back({name, qq, vv, mm, ll});
        skip_ws();
        if (pos < input_str.size() && input_str[pos] == ',') pos++;
        else if (pos < input_str.size() && input_str[pos] == '}') {
            pos++;
            break;
        }
    }
    assert(items.size() == 12);
    auto combined_pri = [&](const Item& it) -> double {
        double cm = (double)it.m / 20000000.0;
        double cv = (double)it.l / 25000000.0;
        double c = cm + cv;
        return c > 0 ? it.v / c : 0;
    };
    auto mass_pri = [&](const Item& it) -> double {
        return it.m > 0 ? it.v / (double)it.m : 0;
    };
    auto vol_pri = [&](const Item& it) -> double {
        return it.l > 0 ? it.v / (double)it.l : 0;
    };
    auto totalv_pri = [&](const Item& it) -> double {
        return (double)it.q * it.v;
    };
    vector<function<double(const Item&)>> strategies = {combined_pri, mass_pri, vol_pri, totalv_pri};
    vector<int> best_cnt(12, 0);
    long long max_val = -1;
    for (const auto& strat : strategies) {
        vector<int> temp(12, 0);
        long long val = greedy(items, temp, strat);
        if (val > max_val) {
            max_val = val;
            best_cnt = temp;
        }
    }
    cout << "{" << endl;
    for (int i = 0; i < 12; i++) {
        if (i > 0) cout << "," << endl;
        cout << " \"" << items[i].name << "\": " << best_cnt[i];
    }
    cout << endl << "}" << endl;
    return 0;
}