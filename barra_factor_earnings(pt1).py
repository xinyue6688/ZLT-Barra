# -*- coding = utf-8 -*-
# @Time: 2024/09/20
# @Author: Xinyue
# @File:barra_factor_earnings(pt1).py
# @Software: PyCharm

import os
import pandas as pd
import pyarrow.parquet as pq
import numpy as np

# 添加行业因子，获取行业数据
ind_df = pd.read_parquet('Data/alpha_beta_all_market.parquet')
# 去除北交所标的
ind_df = ind_df[~ind_df['S_INFO_WINDCODE'].str.endswith('BJ')]

'''# 转换为行业dummy列
industry_dummies = pd.get_dummies(ind_df['WIND_PRI_IND'], dtype=int)
# 合并到原dataframe
df_with_industry_exposure = pd.concat([ind_df, industry_dummies], axis=1)
# 去除原行业列
df_with_industry_exposure = df_with_industry_exposure.drop(columns=['WIND_PRI_IND'])'''

# 按日期升序排列，重设索引
ind_df.sort_values(by = 'TRADE_DT', inplace = True)
ind_df.reset_index(drop=True, inplace=True)

# 添加T+1收益列
ind_df['RETURN_T1'] = ind_df.groupby('S_INFO_WINDCODE')['STOCK_RETURN'].shift(-1).reset_index(drop=True)
ind_df.dropna(subset = 'RETURN_T1', inplace = True)

# 添加国家因子，每个标的对国家因子的暴露恒为1
ind_df['COUNTRY'] = 1
# 保留BETA因子不为空的列
ind_df.dropna(subset = 'BETA', inplace = True)

# 定义目标路径
folder_path = '/Volumes/quanyi4g/factor/day_frequency/barra'
# 获取除Beta外的风格因子文件夹
factors = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
factors.remove('Beta')

# 记录每个因子的有值率
coverage_stats = {}

# 初始化 merged_df，用于存储合并后的数据
merged_df = ind_df.copy()

# 遍历每个因子文件夹并读取数据
for factor in factors:

    # 读取每个风格因子的 parquet 文件
    table = pq.read_table(f'{folder_path}/{factor}')
    df = table.to_pandas()

    # 使用 S_INFO_WINDCODE 和 TRADE_DT 作为键进行合并，并仅添加新的因子列
    merged_df = pd.merge(merged_df, df, on=['S_INFO_WINDCODE', 'TRADE_DT'], how='left')

    # 确保 merged_df 按日期升序排列
    if not merged_df['TRADE_DT'].is_monotonic_increasing:
        merged_df.sort_values(by='TRADE_DT', inplace=True)

    # 获取新增因子列
    new_column = merged_df.columns[-1]

    # 计算原始有值率
    pre_ffill_non_null = merged_df[new_column].notna().mean()

    # 按标的分组，每次新增的因子值空值向后填充
    merged_df[new_column] = merged_df.groupby('S_INFO_WINDCODE')[new_column].ffill()

    # 计算第一次填充后的有值率
    post_ffill_non_null = merged_df[new_column].notna().mean()

    # 剩余空值按截面平均填充
    merged_df[new_column] = merged_df.groupby('TRADE_DT')[new_column].transform(lambda x: x.fillna(x.mean()))

    # 计算第二次填充后的有值率
    post_fillna_non_null = merged_df[new_column].notna().mean()

    # 保存当前因子的有值率统计
    coverage_stats[factor] = {
        'original_non_null': pre_ffill_non_null,
        'post_ffill': post_ffill_non_null,
        'post_cs_mean_fill': post_fillna_non_null
    }

    merged_df = merged_df[merged_df[new_column].notna()]
    merged_df.to_parquet('Data/style_factors_updated.parquet', index = False)
    print(f'Factor: {factor} merged')

# 打印统计结果
for factor, stats in coverage_stats.items():
    print(f"Factor: {factor}")
    print(f"Pre-ffill non-null rate: {stats['original_non_null']:.4f}")
    print(f"Post-ffill non-null rate: {stats['post_ffill']:.4f}")
    print(f"Post-fillna non-null rate: {stats['post_cs_mean_fill']:.4f}\n")


'''from linearmodels.panel.model import FamaMacBeth
merged_df['TRADE_DT'] = pd.to_datetime(merged_df['TRADE_DT'])

merged_df.set_index(['S_INFO_WINDCODE', 'TRADE_DT'], inplace=True)

# Assuming RETURN_T1 is the dependent variable and the other columns are independent variables
y = merged_df['RETURN_T1']
X = merged_df[['Communication Services', 'Consumer Discretionary',
               'Consumer Staples', 'Energy', 'Financials',
               'Health Care', 'Industrials', 'Information Technology',
               'Materials', 'Real Estate', 'Utilities', 'COUNTRY',
               'RSTR', 'LNCAP', 'EARNYILD', 'GROWTH', 'LEVERAGE',
               'LIQUIDITY', 'RESVOL', 'BTOP', 'NLSIZE', 'BETA']]

# Create a copy of X to ensure the original DataFrame is not affected
X_clean = X.copy()
X_clean = X_clean.drop(columns=['Utilities'])

# Step 3: Ensure y aligns with the cleaned X
y_clean = y.loc[X_clean.index]
model = FamaMacBeth(y_clean, X_clean)
result = model.fit()

# Factor returns (coefficients)
factor_returns = result.params
print(factor_returns)

result = model.fit()
print(result.summary)




'''