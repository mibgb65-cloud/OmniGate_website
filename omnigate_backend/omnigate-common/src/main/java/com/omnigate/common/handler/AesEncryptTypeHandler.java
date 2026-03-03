package com.omnigate.common.handler;

import cn.hutool.core.util.HexUtil;
import cn.hutool.crypto.SecureUtil;
import cn.hutool.crypto.symmetric.AES;
import lombok.extern.slf4j.Slf4j;
import org.apache.ibatis.type.BaseTypeHandler;
import org.apache.ibatis.type.JdbcType;
import org.apache.ibatis.type.MappedJdbcTypes;
import org.apache.ibatis.type.MappedTypes;

import java.nio.charset.StandardCharsets;
import java.sql.CallableStatement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * MyBatis-Plus 通用 AES 字符串加解密处理器。
 * <p>
 * 写入数据库时自动加密；查询回填时自动解密。
 * </p>
 */
@Slf4j
@MappedTypes(String.class)
@MappedJdbcTypes(value = {JdbcType.VARCHAR, JdbcType.CHAR, JdbcType.LONGVARCHAR}, includeNullJdbcType = true)
public class AesEncryptTypeHandler extends BaseTypeHandler<String> {

    private static final String AES_KEY_PROPERTY = "omnigate.security.aes.key";
    private static final String AES_KEY_ENV = "OMNIGATE_SECURITY_AES_KEY";
    private static final String DEFAULT_AES_KEY = "OmniGate-Default-AES-Key";

    private static final AES AES = SecureUtil.aes(resolveAesKey());

    /**
     * 将明文参数加密后写入数据库。
     *
     * @param ps PreparedStatement
     * @param i 参数位置
     * @param parameter 明文参数
     * @param jdbcType JDBC 类型
     * @throws SQLException SQL 异常
     */
    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, String parameter, JdbcType jdbcType) throws SQLException {
        if (parameter.isEmpty()) {
            ps.setString(i, "");
            return;
        }
        ps.setString(i, AES.encryptBase64(parameter, StandardCharsets.UTF_8));
    }

    /**
     * 通过列名读取并解密字段值。
     *
     * @param rs ResultSet
     * @param columnName 列名
     * @return 明文值
     * @throws SQLException SQL 异常
     */
    @Override
    public String getNullableResult(ResultSet rs, String columnName) throws SQLException {
        return decryptSafely(rs.getString(columnName), columnName);
    }

    /**
     * 通过列索引读取并解密字段值。
     *
     * @param rs ResultSet
     * @param columnIndex 列索引
     * @return 明文值
     * @throws SQLException SQL 异常
     */
    @Override
    public String getNullableResult(ResultSet rs, int columnIndex) throws SQLException {
        return decryptSafely(rs.getString(columnIndex), "index:" + columnIndex);
    }

    /**
     * 通过存储过程结果读取并解密字段值。
     *
     * @param cs CallableStatement
     * @param columnIndex 列索引
     * @return 明文值
     * @throws SQLException SQL 异常
     */
    @Override
    public String getNullableResult(CallableStatement cs, int columnIndex) throws SQLException {
        return decryptSafely(cs.getString(columnIndex), "callableIndex:" + columnIndex);
    }

    /**
     * 安全解密：当字段为空或解密失败时不抛出异常，保证业务可用性。
     *
     * @param cipherText 密文
     * @param column 字段定位信息
     * @return 明文；若解密失败返回原值
     */
    private String decryptSafely(String cipherText, String column) {
        if (cipherText == null || cipherText.isEmpty()) {
            return cipherText;
        }
        try {
            return AES.decryptStr(cipherText, StandardCharsets.UTF_8);
        } catch (Exception ex) {
            log.warn("AES 解密失败，字段={}, 将回退返回原值。", column);
            return cipherText;
        }
    }

    /**
     * 解析全局 AES 密钥。
     * <p>
     * 优先级：JVM 参数 {@code -Domnigate.security.aes.key}
     * > 环境变量 {@code OMNIGATE_SECURITY_AES_KEY}
     * > 默认常量。
     * </p>
     *
     * @return 32 字节 AES 密钥
     */
    private static byte[] resolveAesKey() {
        String keySource = System.getProperty(AES_KEY_PROPERTY);
        if (keySource == null || keySource.isBlank()) {
            keySource = System.getenv(AES_KEY_ENV);
        }
        if (keySource == null || keySource.isBlank()) {
            keySource = DEFAULT_AES_KEY;
        }
        return HexUtil.decodeHex(SecureUtil.sha256(keySource));
    }
}
